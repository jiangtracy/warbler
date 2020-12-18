"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_user_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Follows, Like


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


class UserViewTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client, add sample data."""

        Follows.query.delete()
        Like.query.delete()
        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        new_user = User.signup(
            username="testuser",
            email="test@test.com",
            password="testuser",
            image_url=None)

        new_user_2 = User.signup(
            username="testuser2",
            email="test@test2.com",
            password="testuser2",
            image_url=None)

        db.session.commit()

        self.testuser_id = new_user.id
        self.testuser2_id = new_user_2.id

    def tearDown(self):
        """ Clean up fouled transactions """

        db.session.rollback()

    def test_users_following(self):
        """ When you’re logged in, can you see the follower / following pages for any user? """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser2_id

        user = User.query.get_or_404(self.testuser_id)
        user2 = User.query.get_or_404(self.testuser2_id)
        user.following.append(user2)
        db.session.commit()
       
        resp = c.get(
                f"/users/{self.testuser_id}/following")

        html = resp.get_data(as_text=True)
        self.assertIn("testuser2", html)
    
    def test_users_following_not_logged_in(self):
        """ When no user is logged in, check that you can't see the follower /following pages for any user.""" 

        user = User.query.get_or_404(self.testuser_id)
        user2 = User.query.get_or_404(self.testuser2_id)
        user.following.append(user2)
        db.session.commit()
       
        resp = self.client.get(
                f"/users/{self.testuser_id}/following",
                follow_redirects=True)

        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Access unauthorized.", html)
        

    

