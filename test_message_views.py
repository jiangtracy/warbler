"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

# set an environmental variable
# to use a different database for tests (do this
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
        # TODO: could make a helper function _def_user_login that gets the user and makes a POST request. Less repetitive with adding to session each time. Test login route more. Could make a helper function that makes a post request to /signup. Make requests to routes that call the methods rather than calling the methods here. 
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
        """Can you add a message?"""

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
            # can make sure resp.data has the new message
            # instead can follow redirects and check the new template
            self.assertEqual(Message.query.count(), 2)

    def test_add_message_logged_out(self):
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
        """ Test to check that you can't add a message if non-nullable field is 
        blank """

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
    # TODO: can make a post request with the user id that doesn't exist.
    # Or can create another user instance and check that the message doesn't have that usernmae
    # def test_add_message_dif_user(self):
    #     """ Test to check that you can't add a message as another user """

    #     with self.client as c:
    #         with c.session_transaction() as sess:
    #             sess[CURR_USER_KEY] = self.testuser_id

    #     resp = c.post(
    #         "/messages/new",
    #         data={"text": "Test Text"},
    #         follow_redirects=True)
    #     html = resp.get_data(as_text=True)

    #     msg = Message.query.filter(Message.text == "Test Text").first()

    #     new_user2 = User.signup(username="testuser2",
    #                         email="test2@test.com",
    #                         password="testuser2",
    #                         image_url=None)

    #     new_user2.messages.append(msg)

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

    def test_messages_destroy_dif_user(self):
        """ Test that you are prohibited from deleting a message as another user """

        new_user2 = User.signup(username="testuser2",
                            email="test2@test.com",
                            password="testuser2",
                            image_url=None)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = new_user2.id
    
            resp = c.post(
                f"/messages/{self.message_id}/delete",
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(Message.query.count(), 1)

    def test_messages_destroy_logged_out(self):
        """ Test that you are prohibited from deleting a message if not logged in"""
    
        with self.client as c:

            resp = c.post(
                f"/messages/{self.message_id}/delete",
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)