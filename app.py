import os
from dotenv import load_dotenv

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, CSRFForm, UserProfileEditForm
from models import db, connect_db, User, Message, DEFAULT_HEADER_IMAGE_URL, DEFAULT_IMAGE_URL

from werkzeug.exceptions import Unauthorized

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# Before_Request functions

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
    else:
        g.user = None


@app.before_request
def add_csrf_to_g():
    """Adds CSRF form to Flask global if ..."""

    g.csrf_form = CSRFForm()



##############################################################################
# User signup/login/logout

def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Log out user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    do_logout()

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login and redirect to homepage on success."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(
            form.username.data,
            form.password.data,
        )

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.post('/logout')
def logout():
    """Handle logout of user and redirect to homepage."""

    form = g.csrf_form

    if form.validate_on_submit():
        do_logout()
        flash ("Successfully logged out.")
    else:
        raise Unauthorized()


    return redirect('/')



##############################################################################
# General user routes:

@app.get('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template(
        'users/index.html',
        users=users,
        form=g.csrf_form
    )


@app.get('/users/<int:user_id>')
def show_user(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    return render_template(
        'users/show.html',
        user=user,
        form=g.csrf_form
    )


@app.get('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    user = User.query.get_or_404(user_id)

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    return render_template(
        'users/following.html',
        user=user,
        form=g.csrf_form
    )


@app.get('/users/<int:user_id>/followers')
def show_followers(user_id):
    """Show list of followers of this user."""

    user = User.query.get_or_404(user_id)

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    return render_template(
        'users/followers.html',
        user=user,
        form=g.csrf_form
    )


@app.post('/users/follow/<int:follow_id>')
def start_following(follow_id):
    """Add a follow for the currently-logged-in user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.post('/users/stop-following/<int:follow_id>')
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user.

    Redirect to following page for the current for the current user.
    """

    followed_user = User.query.get_or_404(follow_id)

    if not g.user or followed_user not in g.user.following:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """GET: Shows user profile edit page.
    POST: Update profile for current user and redirects to user detail page."""
    #TODO: Reassign g.user to global variable name
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = UserProfileEditForm(obj=g.user)

    if form.validate_on_submit():
        #form.username.data etc.
        g.user.username = request.form.get('username', g.user.username)
        g.user.email = request.form.get('email', g.user.email)
        g.user.bio = request.form.get('bio')

        # g.user.image_url = form.image_url.data or DEFAULT

        if request.form.get("image_url") == "":
            g.user.image_url = DEFAULT_IMAGE_URL
        else:
            g.user.image_url = request.form.get("image_url")

        if request.form.get("header_image_url") == "":
            g.user.header_image_url = DEFAULT_HEADER_IMAGE_URL
        else:
            g.user.header_image_url = request.form.get("header_image_url")

        if User.authenticate(g.user.username, request.form.get('password')):
            db.session.commit()
            return redirect(f'/users/{g.user.id}')

        #TODO: Wrap more logic in authentication
        #TODO: Trim defensive logic

    flash("Invalid password")
    return render_template('users/edit.html', user=g.user, form=form)


@app.post('/users/delete')
def delete_user():
    """Delete user.

    Redirect to signup page.
    """
    #TODO: CSRF form, duh.

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")



##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def add_message():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/create.html', form=form)


@app.get('/messages/<int:message_id>')
def show_message(message_id):
    """Show a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', message=msg, form=g.csrf_form)


@app.post('/messages/<int:message_id>/delete')
def delete_message(message_id):
    """Delete a message.

    Check that this message was written by the current user.
    Redirect to user page on success.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")



##############################################################################
# Homepage and error pages

@app.get('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of self & followed_users
    """

    if g.user:
        valid_ids = [ f.id for f in g.user.following ]
        valid_ids.append(g.user.id)

        messages = (
            Message.
            query.
            filter(Message.user_id.in_(valid_ids))
            .order_by(Message.timestamp.desc())
            .limit(100)
            .all()
        )

        return render_template('home.html', messages=messages, form=g.csrf_form)

    else:
        return render_template('home-anon.html')


@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
