"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Now we can import app

from app import app, CURR_USER_KEY

# This is a bit of hack, but don't use Flask DebugToolbar
app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

# Make Flask errors be real errors, rather than HTML pages with error info
app.config['TESTING'] = True

# Turn off debugtoolbar intercept redirects
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        new_user = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()

        self.testuser_id = new_user.id

        message_data = {
            "user_id": self.testuser_id,
            "text": "test_message"
        }

        # store the id instead, otherwise might be bound to session
        message = Message(**message_data)
        db.session.add(message)
        db.session.commit()

        self.message_id = message.id

    def tearDown(self):
        """ Clean up fouled transactions """

        db.session.rollback()

    def test_add_message(self):
        """Can use add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post(
                "/messages/new", 
                data={"text": "Hello"}, 
                follow_redirects=False)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(Message.query.count(), 2)

    def test_add_message_fail(self):
        """ Test to check that you can't add a message if you are not logged in
        """

        with self.client as c:

            # If we don't add testuser.id to session, the server should not let 
            # user add a message

            resp = c.post(
                "/messages/new",
                data={"text": "Hello"},
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)

    def test_add_message_form_fail(self):
        """ Test to check that you can't add a message if you are not logged in
        """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            # If we don't add text to the message, the form should be invalid

            resp = c.post(
                "/messages/new", 
                data={"text": ""}, 
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Add my message!", html)
            self.assertEqual(Message.query.count(), 1)


    def test_messages_show(self):
        """ Test to a message being shown. """

        with self.client as c:
            # print(self.message.id)
            resp = c.get(f"/messages/{self.message_id}")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("test_message", html)

    def test_messages_destroy(self):
        """ Test deleting a message """
     
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id
    
            resp = c.post(
                f"/messages/{self.message_id}/delete",
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("test_message", html)

            self.assertEqual(Message.query.count(), 0)