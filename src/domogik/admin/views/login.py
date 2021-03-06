from domogik.admin.application import app, login_manager, babel, render_template
from flask import request, flash, redirect, Response
from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage
from flask_login import login_required, login_user, logout_user, current_user
from wtforms import form, fields, validators
from flask.ext.babel import gettext, ngettext, get_locale

class LoginForm(form.Form):
    user = fields.TextField('user', [validators.Required()])
    passwd = fields.PasswordField('passwd', [validators.Required()])
    def hidden_tag(self):
        pass

@login_manager.user_loader
def load_user(userid):
    # Used if we already have a cookie
    with app.db.session_scope():
        user = app.db.get_user_account(userid)
        app.db.detach(user)
        if user.is_admin:
            return user
        else:
            return None

@login_manager.unauthorized_handler
def rediret_to_login():
    if str(request.path).startswith('/rest/'):
        if app.rest_auth == 'True':
            # take into account that json_reponse is called after this, so we need to pass th params to json_reponse
            return 401, "Could not verify your access level for that URL.\n You have to login with proper credentials."
        else:
            pass
    else:
        return redirect('/login')

@login_manager.request_loader
def load_user_from_request(request):
    if str(request.path).startswith('/rest/'):
        if app.rest_auth == 'True':
            auth = request.authorization
            if not auth:
                return None
            else:
                with app.db.session_scope():
                    if app.db.authenticate(auth.username, auth.password):
                        user = app.db.get_user_account_by_login(auth.username)
                        if user.is_admin:
                            return user
                        else:
                            return None
                    else:
                            return None
        else:
            with app.db.session_scope():
                user = app.db.get_user_account_by_login('Anonymous')
                return user
    else:
        return None

@babel.localeselector
def get_locale():
    return 'en'


@app.route('/login', methods=('GET', 'POST'))
def login():
    fform = LoginForm(request.form)
    if request.method == 'POST' and fform.validate():
        with app.db.session_scope():
            if app.db.authenticate(request.form["user"], request.form["passwd"]):
                user = app.db.get_user_account_by_login(request.form["user"])
                if user.is_admin:
                    login_user(user)
                    # as we see the page after the login, there is no need to tell this is a success ;)
                    #flash(gettext("Login successfull"), "success")
                    return redirect('/')
                else:
                    flash(gettext("This user is not an admin"), "warning")
            else:
                flash(gettext("Combination of username and password wrong"), "warning")
    return render_template('login.html',
        form=fform,
        nonav = True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/login")
