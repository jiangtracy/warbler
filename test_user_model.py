"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows, Like
from sqlalchemy.exc import IntegrityError
from flask_bcrypt import Bcrypt

# set an environmental variable
# to use a different database for tests (do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Now we can import app

from app import app

# This is a bit of hack, but don't use Flask DebugToolbar
app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

# Make Flask errors be real errors, rather than HTML pages with error info
app.config['TESTING'] = True

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()
bcrypt = Bcrypt()

USER_DATA = {
    "email":"test@test.com",
    "username":"testuser",
    "password":"HASHED_PASSWORD"
}

USER_DATA_2 = {
    "email":"test2@test.com",
    "username":"testuser2",
    "password":"HASHED_PASSWORD2"
}


USER_DATA_3 = {
    "email":"test3@test.com",
    "username":"testuser3",
    "password":"HASHED_PASSWORD3",
    "image_url": User.image_url.default.arg
}

class UserModelTestCase(TestCase):
    """Tests for user model."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()
        Like.query.delete()

        self.client = app.test_client()

        u = User(**USER_DATA)
        u2 = User(**USER_DATA_2)

        
        db.session.add(u)
        db.session.add(u2)
        db.session.commit()
        # TODO: change this to storing self.user_id instead of the instance itself
        self.user = u
        self.user2 = u2

    def tearDown(self):
        """ Clean up fouled transactions """

        db.session.rollback()

    def test_user_model(self):
        """Does basic model work?"""

        # User should have no messages, no liked messages & no followers
        # TODO: write more specific test (don't test characteristic, test the item itself, like an empty list)
        self.assertEqual(len(self.user.messages), 0)
        self.assertEqual(len(self.user.followers), 0)
        self.assertEqual(len(self.user.liked_messages), 0)
        self.assertEqual(
            str(self.user), 
            f"<User #{self.user.id}: testuser, test@test.com>")

    def test_user_is_following(self):
        """ Does is_following successfully detect when user1 is following 
        user2 and detect when user1 is not following user2? """

        # test if is_following detects when user1 is following user2
        self.user.following.append(self.user2)
        # TODO: test the list of is_following itself
        self.assertTrue(self.user.is_following(self.user2))

        # test if is_following detects when user1 is not following user2
        self.user.following.remove(self.user2)
        self.assertFalse(self.user.is_following(self.user2))

    def test_user_is_followed_by(self):
        """ Does is_followed_by successfully detect when user1 is followed by 
        user2 and detect when user1 is not followed by user2? """

        # test if is_followed_by detects when user1 is following user2
        self.user.followers.append(self.user2)
        self.assertTrue(self.user.is_followed_by(self.user2))

        # test if is_followed_by detects when user1 is not following user2
        self.user.followers.remove(self.user2)
        self.assertFalse(self.user.is_followed_by(self.user2))

    def test_user_signup(self):
        """ Does User.signup() successfuly create a new user given valid 
        credentials """

        new_user = User.signup(**USER_DATA_3)
        db.session.commit()

        self.assertIsInstance(new_user.id, int)
        self.assertEqual(User.query.count(), 3)

    def test_user_signup_fail(self):
        """ Does User.signup() fail to create a new user given invalid 
        credentials """

        # check that signup fails if non-nullable argument is not passed in
        USER_DATA_3.pop('username')
        # TODO: note that we can also do try/ except in tests
        with self.assertRaises(TypeError):
            new_user = User.signup(**USER_DATA_3)

        self.assertEqual(User.query.count(), 2)

        # check that signup fails if unique validation fails
        USER_DATA_3['username'] = USER_DATA['username']
        with self.assertRaises(IntegrityError):
            new_user = User.signup(**USER_DATA_3)
            db.session.commit()

        # in a transaction, if one fails, all after will fails, can be reset with db.session.rollback()
        db.session.rollback()

        self.assertEqual(User.query.count(), 2)

    def test_user_authenticate(self):
        """ Test if User.authenticate return a user when given a valid username and password and return false when passing in invalid username/password"""

        original_pw = USER_DATA_3['password']
        USER_DATA_3['password'] = bcrypt.generate_password_hash(
            USER_DATA_3['password']).decode('UTF-8')
        new_user = User(**USER_DATA_3)

        db.session.add(new_user)
        db.session.commit()

        # Test if successfully authenticate by passing valid username and password 
        self.assertEqual(
            User.authenticate(USER_DATA_3['username'], original_pw), new_user)

        # Test if failed to authenticate by passing invalid password 
        self.assertFalse(
            User.authenticate(USER_DATA_3['username'], 'testuser2')
        )

        # Test if failed to authenticate by passing invalid username
        self.assertFalse(
            User.authenticate('invalid_username', original_pw)
        )
    



