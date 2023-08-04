"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from models import db, User, Message

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()

class MessageModelTestCase(TestCase):
    def setUp(self):
        Message.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)

        m1 = Message(
            text="sometimes ham",
            timestamp=None
        )

        u1.messages.append(m1)

        db.session.commit()

        self.u1_id = u1.id


    def tearDown(self):
        db.session.rollback()


    def test_message_model(self):
        """Tests Message model attributes"""

        u1 = User.query.get(self.u1_id)

        self.assertEqual(len(u1.messages), 1)

        m2 = Message(
            text="pineapple pizza",
            timestamp=None
        )

        u1.messages.append(m2)

        self.assertEqual(len(u1.messages), 2)

        self.assertEqual(u1.messages[1].text, "pineapple pizza")



