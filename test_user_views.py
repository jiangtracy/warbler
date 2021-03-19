"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_user_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Follows, Like


# BEFORE we import our app, set an environmental variable
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


class UserViewTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client, add sample data."""

        Follows.query.delete()
        Like.query.delete()
        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()
        #  TODO: helper function that calls user.signup
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
        """ When you’re logged in, can you see the following pages for any user? """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser2_id

        user = User.query.get(self.testuser_id)
        user2 = User.query.get(self.testuser2_id)
        user.following.append(user2)
        db.session.commit()
       
        resp = c.get(
                f"/users/{self.testuser_id}/following")

        html = resp.get_data(as_text=True)
        self.assertIn("testuser2", html)
    
    def test_users_following_logged_out(self):
        """ When no user is logged in, check that you can't see the following pages for any user.""" 

        user = User.query.get(self.testuser_id)
        user2 = User.query.get(self.testuser2_id)
        user.following.append(user2)
        db.session.commit()
       
        resp = self.client.get(
                f"/users/{self.testuser_id}/following",
                follow_redirects=True)

        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Access unauthorized.", html)
        
    def test_users_followers(self):
        """ When you’re logged in, can you see the follower pages for any user? """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser2_id

        user = User.query.get(self.testuser_id)
        user2 = User.query.get(self.testuser2_id)
        user.followers.append(user2)
        db.session.commit()
       
        resp = c.get(
                f"/users/{self.testuser_id}/followers")

        html = resp.get_data(as_text=True)
        self.assertIn("testuser2", html)
    
    def test_users_followers_logged_out(self):
        """ When no user is logged in, check that you can't see the followers pages for any user.""" 

        user = User.query.get(self.testuser_id)
        user2 = User.query.get(self.testuser2_id)
        user.followers.append(user2)
        db.session.commit()
       
        resp = self.client.get(
                f"/users/{self.testuser_id}/followers",
                follow_redirects=True)

        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Access unauthorized.", html)

    def test_login(self):
        """ Test login successfully works """

        user = User.query.get(self.testuser_id)

        with self.client as c:
            resp = c.post(
                "/login",
                data={
                    "username":user.username,
                    "password":"testuser"
                    }, 
                follow_redirects=True)
            
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"Hello, {user.username}!", html)

    def test_login_fail(self):
        """ Test login does not work with invalid credentials """

        user = User.query.get_or_404(self.testuser_id)

        with self.client as c:
            resp = c.post(
                "/login",
                data={
                    "username":user.username,
                    "password":"wrong password"
                    }, 
                follow_redirects=True)
            
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Invalid credentials", html)

    def test_logout(self):
        """ Test logout successfully works """
        # TODO: can check the session
        with self.client as c:
            resp = c.post(
                "/logout",
                follow_redirects=True)
            
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Successfully logged out!", html)

    def test_user_profile(self):
        """ Test successful update profile """

        user = User.query.get(self.testuser_id)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.post(
                    "/users/profile",
                    data={
                        "username":user.username,
                        "email":user.email,
                        "image_url":user.image_url,
                        "header_image_url":user.header_image_url,
                        "bio":"new bio!",
                        "password":"testuser",
                        }, 
                    follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("new bio!", html)

    def test_user_profile_invalid_cred(self):
        """ Test that you cannot update user profile with wrong password """

        user = User.query.get(self.testuser_id)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id
            # TODO: potential helper function or factory with data
            resp = c.post(
                    "/users/profile",
                    data={
                        "username":user.username,
                        "email":user.email,
                        "image_url":user.image_url,
                        "header_image_url":user.header_image_url,
                        "bio":"new bio!",
                        "password":"wrong password",
                        }, 
                    follow_redirects=True)
            html = resp.get_data(as_text=True)
            
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Invalid Password", html)

    def test_user_profile_logged_out(self):
        """ Test that you cannot update user profile if you are logged out """

        user = User.query.get(self.testuser_id)

        with self.client as c:

            resp = c.post(
                    "/users/profile",
                    data={
                        "username":user.username,
                        "email":user.email,
                        "image_url":user.image_url,
                        "header_image_url":user.header_image_url,
                        "bio":"new bio!",
                        "password":"testuser",
                        }, 
                    follow_redirects=True)
            html = resp.get_data(as_text=True)
            
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", html)

    def test_user_profile_invalid_form(self):
        """ Test that the user will not be updated with invalid form submission"""

        user = User.query.get_or_404(self.testuser_id)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.post(
                    "/users/profile",
                    data={
                        "username":"",
                        "email":user.email,
                        "image_url":user.image_url,
                        "header_image_url":user.header_image_url,
                        "bio":"new bio!",
                        "password":"testuser",
                        }, 
                    follow_redirects=True)
            html = resp.get_data(as_text=True)
            
            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"{user.image_url}", html)
        
            user = User.query.get_or_404(self.testuser_id)
            # check that username is equal to original username. Want tests to be more specific 
            self.assertNotEqual(user.username, "")

    def test_user_delete(self):
        """ Test delete user"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.post(
                    "/users/delete",
                    follow_redirects=True)
            html = resp.get_data(as_text=True)
            
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Join Warbler today.", html)
            self.assertEqual(User.query.count(), 1)

    def test_user_delete_logged_out(self):
        """ Test that you cannot delete user if you are logged out"""

        with self.client as c:

            resp = c.post(
                    "/users/delete",
                    follow_redirects=True)
            html = resp.get_data(as_text=True)
            # TODO: check the session
            # from flask import session, then check if curr user key is in the session
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", html)