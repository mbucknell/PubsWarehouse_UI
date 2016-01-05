from itsdangerous import BadSignature, BadPayload
from requests import post

from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

from flask import render_template, request, flash, redirect, url_for, Blueprint
from flask.ext.login import LoginManager, logout_user, UserMixin, login_user
from flask.ext.wtf import Form

from . import login_serializer
from .utils import get_cida_auth_token, generate_auth_header, get_url_endpoint, is_safe_url
from .. import app


auth = Blueprint('auth', __name__,
                 template_folder='templates',
                 static_folder='static',
                 static_url_path='/auth/static')

AUTH_ENDPOINT_URL = app.config.get('AUTH_ENDPOINT_URL')
# should requests verify the certificates for ssl connections
VERIFY_CERT = app.config['VERIFY_CERT']


class LoginForm(Form):
    username = StringField('AD Username:', validators=[DataRequired()])
    password = PasswordField('AD Password:', validators=[DataRequired()])

# Flask-Login Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login_page'

class User(UserMixin):
    """
    User Class for flask-Login
    """
    def __init__(self, username=None, cida_auth_token=None):
        self.id = username
        self.cida_auth_token = cida_auth_token

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_auth_token(self):
        """
        Encode a secure token for cookie.

        The Token is encrypted using itsdangerous.URLSafeTimedSerializer which
        allows us to have a max_age on the token itself.  When the cookie is stored
        on the users computer it also has a exipry date, but could be changed by
        the user, so this feature allows us to enforce the exipry date of the token
        server side and not rely on the users cookie to exipre.
        """
        data = [str(self.id), self.cida_auth_token]
        return login_serializer.dumps(data)

    @staticmethod
    def get(username, cida_auth_token):
        '''
        :param username: AD username
        :param cida_auth_token: token returned by CIDA auth service
        :return User object if userid is valid, otherwise return None:
        '''
        if username:
            user = User(username, cida_auth_token)
        else:
            user = None
        return user


@login_manager.user_loader
def load_user(username):
    """
    Flask-Login user_loader callback.
    The user_loader function reloads the user object from the user ID stored in the session.
    """
    cida_auth_token = get_cida_auth_token(request.cookies)
    if cida_auth_token:
        user = User.get(username, cida_auth_token)
    else:
        user = None

    return user


@login_manager.token_loader
def load_token(token):
    """
    Flask-Login token_loader callback.
    The token_loader function asks this function to take the token that was
    stored on the users computer process it to check if its valid and then
    return a User Object if its valid or None if its not valid.
    """

    # The Token itself was generated by User.get_auth_token.  So it is up to
    # us to known the format of the token data itself.
    # Decrypt the Security Token, data = [ad_user_username, user_ad_token]
    try:
        data = login_serializer.loads(token, max_age=app.config['REMEMBER_COOKIE_DURATION'].total_seconds())
    except (BadSignature, BadPayload):
        user = None
    else:
        # generate the user object based on the contents of the cookie, if the cookie isn't expired
        if data:
            user = User(data[0], data[1])
        else:
            user = None

    return user

@auth.route("/logout/<forward>")
def logout_page(forward):
    """
    Web Page to Logout User, then Redirect them to Index Page.
    """
    auth_header = generate_auth_header(request)
    logout_url = AUTH_ENDPOINT_URL + 'logout'
    response = post(logout_url, headers=auth_header, verify=VERIFY_CERT)
    if response.status_code == 200:
        print 'logout works!'

    logout_user()

    return redirect(url_for(forward))


@auth.route("/login/", methods=["GET", "POST"])
def login_page():
    """
    Web Page to Display Login Form and process form.
    """
    form = LoginForm()
    error = None
    if request.method == "POST":
        # take the form data and put it into the payload to send to the pubs auth endpoint
        payload = {'username': request.form['username'], 'password': request.form['password']}
        # POST the payload to the pubs auth endpoint
        pubs_login_url = AUTH_ENDPOINT_URL + 'token'
        mp_response = post(pubs_login_url, data=payload, verify=VERIFY_CERT)
        # if the pubs endpoint login is successful, then proceed with logging in
        if mp_response.status_code == 200:
            user = User(request.form['username'], mp_response.json().get('token'))
            login_user(user, remember=True)

            next_page = request.args.get("next")
            app.logger.info("Next page: %s" % next_page)

            if next_page is not None and is_safe_url(next_page, request.host_url):
                endpoint = get_url_endpoint(next_page, request.environ['SERVER_NAME'], ('pubswh.index', {}))
                url = url_for(endpoint[0], **endpoint[1])
                return redirect(url)

            else:
                return redirect(url_for('pubswh.index'))
        else:
            error = 'Username or Password is invalid '+str(mp_response.status_code)

    return render_template("auth/login.html", form=form, error=error)

@auth.route('/loginservice/', methods=["POST"])
def login_service():
    resp = post(AUTH_ENDPOINT_URL + 'token', data=request.form, verify=VERIFY_CERT)
    if resp.status_code == 200:
        user = User(request.form['username'], resp.json().get('token'))
        login_user(user, remember=True)

    # This fixed an an ERR_INVALID_CHUNKED_ENCODING when the app was run on the deployment server.
    if 'transfer-encoding' in resp.headers:
        del resp.headers['transfer-encoding']
    return (resp.text, resp.status_code, resp.headers.items())

