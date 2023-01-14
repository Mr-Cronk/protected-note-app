import os
import secrets
import time
from PIL import Image
from sqlalchemy.sql.expression import or_
from flask import render_template, url_for, flash, redirect, request, abort, session
from main import app, db, bcrypt
from main.forms import PostForm, RegistrationForm, LoginForm, UpdateAccountForm, DecryptForm
from main.models import User, Post
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import or_, and_
import re
import jinja2


def show_as_encrypted(post):
    post.content = '***content encrypted***'
    return


def find_viewers(text):
    matches = [t.strip('@;,!?.') for t in text.split() if t.startswith('@')]
    print(matches)
    return matches


@app.route("/")
@app.route("/index")
def index():
    page = request.args.get('page', 1, type=int)
    if current_user.is_authenticated and not current_user.is_anonymous and current_user.is_active and current_user.username:
        posts = db.session.query(Post).filter(
            or_(and_(Post.encrypt == False, Post.group_note == True, Post.author == current_user),
                and_(Post.encrypt == False, Post.group_note == True, Post.viewers.any(id=current_user.id)),
                and_(Post.encrypt == False, Post.group_note == False),
                and_(Post.author == current_user, Post.encrypt == True))) \
            .order_by(Post.date_posted.desc())
        for post in posts:
            if post.encrypt:
                post = show_as_encrypted(post)
        posts = posts.paginate(page=page, per_page=5)
    else:
        posts = Post.query.filter(and_(Post.encrypt == False, Post.group_note == False)).order_by(
            Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template("index.html", posts=posts)


@app.route("/about")
def about():
    return render_template("about.html", title="about")


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}! You can login now', 'success')
        return redirect(url_for('login'))
    return render_template("register.html", title="Register", form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user:
            time.sleep(2 ** user.attempts)
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            user.attempts = 0
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            if user:
                user.attempts += 1
                db.session.commit()
                flash(f'Login unsuccessful, attempts: {user.attempts}, therefore login will take {2 ** user.attempts}s',
                      'danger')
            else:
                flash(f'Login unsuccessful', 'danger')
    return render_template("login.html", title="Login", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('index'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    img = Image.open(form_picture)
    img.thumbnail(output_size)

    img.save(picture_path)
    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            old_file = current_user.image_file
            old_path = os.path.join(app.root_path, 'static/profile_pics', old_file)

            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
            if (os.path.exists(old_path) and old_file != 'default.jpg'):
                os.remove(old_path)

        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template("account.html", title="Account", image_file=image_file, form=form)
