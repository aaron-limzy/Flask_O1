from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, HiddenField, FloatField, FormField, IntegerField, DecimalField, RadioField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length, NumberRange, InputRequired, AnyOf
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask_uploads import UploadSet, IMAGES, configure_uploads
from app import excel_format
from app.models import *

# Configure the image uploading via Flask-Uploads
#images = UploadSet('files',  extensions=('xls', 'xlsx', 'csv'))


class MT5_Modify_Trades_Form(FlaskForm):
    MT5_Login = IntegerField('User Login', validators=[DataRequired()])
    MT5_Deal_Num = IntegerField('Deal Number', validators=[DataRequired()])
    MT5_Comment = StringField('Comment')
    MT5_Action = RadioField("Action", choices=[("delete",'Delete'),("change comment",'Change Comment')], validators=[DataRequired()])
    #upload = FileField('Excels', validators=[FileAllowed(excel_format,  'CSV Files only!')])
    submit = SubmitField('Upload')

class File_Form(FlaskForm):
    upload = FileField('Excels', validators=[FileAllowed(excel_format,  'CSV Files only!')])



class UploadForm(FlaskForm):
    #recipe_title = StringField('Recipe Title', validators=[DataRequired()])
    #recipe_description = StringField('Recipe Description', validators=[DataRequired()])
    #recipe_image = FileField('Recipe Image', validators=[FileRequired(), FileAllowed(images, 'Excel Files only!')])
    upload = FileField('Excels', validators=[FileRequired(),
        FileAllowed(excel_format,  'CSV Files only!')])
    submit = SubmitField('Upload')


class SymbolSwap(FlaskForm):
    Symbol = StringField('Symbol')
    Short = FloatField('Short', validators=[DataRequired()])
    Long = FloatField('Long', validators=[DataRequired()])


class SymbolTotal(FlaskForm):
    Symbol_individual = FormField(SymbolSwap)


class SymbolTotalTest(FlaskForm):
    submit = SubmitField('Upload')

    @classmethod
    def append_field(cls, name, field):
        setattr(cls, name, field)
        return cls


class AddOffSet(FlaskForm):
    Symbol = StringField('Symbol', validators=[DataRequired()])
    Offset = DecimalField('Offset BGI Lots', places=2,rounding=None,  validators=[InputRequired()])
    Ticket = IntegerField("BGI Ticket #", validators=[DataRequired()])
    LP =  StringField('LP (Trade to which LP)', validators=[DataRequired()])
    Comment = StringField('Comment (If any)')
    submit = SubmitField('Submit')



class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

# For Creating User Form. Need them to submit password twice.
class CreateUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email =  StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('New Password', [InputRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm  = PasswordField('Repeat Password')
    submit = SubmitField('Create User')



# Want to add into SQL for change group, when there are no open trades.
class noTrade_ChangeGroup_Form(FlaskForm):
    Live = IntegerField('Live', validators=[DataRequired(), AnyOf(values=[1,2,3,5], message="Only Live 1,2,3 and 5")])
    Login = IntegerField('Login', validators=[DataRequired()])
    Current_Group = StringField('Current Group', validators=[DataRequired()])
    New_Group = StringField('New Group', validators=[DataRequired()])
    submit = SubmitField('Submit')