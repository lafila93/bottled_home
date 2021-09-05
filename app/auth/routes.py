from app.auth.forms import LoginForm
from app import models
from app.auth import bp
from flask import flash, redirect, render_template, request, url_for
from flask.helpers import make_response
from flask_login import current_user, login_user, logout_user


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = models.User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password", "warning")
            return redirect(url_for("auth.login"))

        login_user(user, remember=form.remember.data)
        
        flash("Successfully logged in", "success")
        next_page = request.args.get("next", url_for("main.index"))

        # add api token to cookies for js ajax calls
        resp = make_response(redirect(next_page))
        resp.set_cookie("api_token", user.create_token(exp=60*60*24*90))
        return resp
    return render_template("auth/login.html", title="Login", form=form)

@bp.route("/logout")
def logout():
    resp = redirect(url_for("main.index"))
    if current_user.is_authenticated:
        logout_user()
        # remove api token from cookies
        flash("Successfully logged out", "success")
        resp.delete_cookie("api_token")
    return resp
