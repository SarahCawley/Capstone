'''
Each class in this file serves as an object relational map for the tables 
in the underlying database. This is done through the use of Flask-SQLAlchemy.
In general, each class function serves only to initialize the object (analogous
to an entry into or already existing in the database) and to represent the object
as a string. The exceptions to this rule can be found in the Account class which
contains a number of getter and setter methods.
'''

from handlers.Database import database
	
class Account (database.db.Model):
	id = database.db.Column(database.db.Integer, primary_key=True)
	pword = database.db.Column(database.db.String(255), nullable=False)
	q1_id = database.db.Column(database.db.Integer, database.db.ForeignKey('question.id',ondelete='RESTRICT',onupdate='RESTRICT'), nullable=False)
	q2_id = database.db.Column(database.db.Integer, database.db.ForeignKey('question.id',ondelete='RESTRICT',onupdate='RESTRICT'), nullable=False)
	answer1 = database.db.Column(database.db.Text, nullable=False)
	answer2 = database.db.Column(database.db.Text, nullable=False)
	created = database.db.Column(database.db.DateTime, nullable=False)
	authenticated = database.db.Column(database.db.Boolean, default=False)
	code = database.db.Column(database.db.Integer,default=None,nullable=True)
	
	admin = database.db.relationship('Admin', backref='account',uselist=False,lazy='joined',cascade='all, delete-orphan')
	manager = database.db.relationship('Manager', backref='account', uselist=False, lazy='joined',cascade='all, delete-orphan')
	q1 = database.db.relationship('Question',foreign_keys=[q1_id])
	q2 = database.db.relationship('Question',foreign_keys=[q2_id])
	
	def __init__(self,pword,q1,q2,a1,a2,created):
		self.pword = pword
		self.q1_id = q1
		self.q2_id = q2
		self.answer1 = a1
		self.answer2 = a2
		self.created = created

	def __repr__(self):
		return '<Account {0}>'.format(self.id)
		
	def is_active(self):
		return True

	def get_id(self):
		return self.id

	def is_authenticated(self):
		return self.authenticated

	def is_anonymous(self):
		return False

class Question(database.db.Model):
		id = database.db.Column(database.db.Integer, primary_key=True)
		prompt = database.db.Column(database.db.String(255), nullable=False)
		
		def __init__(self,prompt):
			self.prompt = prompt
			
		def __repr__(self):
			return '{0}'.format(self.prompt)		
	
class Admin (database.db.Model):
	id = database.db.Column(database.db.Integer, primary_key=True)
	account_id = database.db.Column(database.db.Integer, database.db.ForeignKey('account.id',ondelete='CASCADE',onupdate='RESTRICT'), nullable=False)
	email = database.db.Column(database.db.String(32), nullable=False, unique=True)
	fname = database.db.Column(database.db.String(32), nullable=False)
	lname = database.db.Column(database.db.String(32), nullable=False)
	
	def __init__(self,account,email,fname,lname):
		self.account = account
		self.email = email
		self.fname = fname
		self.lname = lname
		
	def __repr__(self):
		return '<Admin {0} {1}>'.format(self.fname,self.lname)


class Manager (database.db.Model):
	id = database.db.Column(database.db.Integer, primary_key=True)
	account_id = database.db.Column(database.db.Integer, database.db.ForeignKey('account.id',ondelete='CASCADE',onupdate='RESTRICT'), nullable=False)
	title = database.db.Column(database.db.String(32), nullable=False)
	fname = database.db.Column(database.db.String(32), nullable=False)
	lname = database.db.Column(database.db.String(32), nullable=False)
	signature = database.db.Column(database.db.Text, nullable=False)
	email = database.db.Column(database.db.String(32), nullable=False, unique=True)
	
	createdBy = database.db.relationship('Award', backref='manager',lazy='dynamic')
	
	def __init__(self,account,title,fname,lname,signature,email):
		self.account = account
		self.title = title
		self.fname = fname
		self.lname = lname
		self.signature = signature
		self.email = email

	def __repr__(self):
		return '<Manager {0}>'.format(self.fname + ' ' + self.lname)


class AwardType (database.db.Model):
	id = database.db.Column(database.db.Integer, primary_key=True)
	name = database.db.Column(database.db.String(32),nullable=False)

	type = database.db.relationship('Award', backref='award_type', lazy='dynamic')

	def __init__(self,name):
		self.name = name

	def __repr__(self):
		return '<AwardType {0}>'.format(self.name)

class Award (database.db.Model):
	id = database.db.Column(database.db.Integer, primary_key=True)
	creator = database.db.Column(database.db.Integer, database.db.ForeignKey('manager.id',ondelete='SET NULL',onupdate='RESTRICT'),nullable=True)
	type_id = database.db.Column(database.db.Integer, database.db.ForeignKey('award_type.id',ondelete='RESTRICT',onupdate='RESTRICT'),nullable=False)
	message = database.db.Column(database.db.String(255),nullable=False)
	issuedOn = database.db.Column(database.db.Date,nullable=False)
	recipient = database.db.Column(database.db.Integer,database.db.ForeignKey('employee.id',ondelete='SET NULL',onupdate='RESTRICT'),nullable=True)
	background_id = database.db.Column(database.db.Integer,database.db.ForeignKey('award_background.id',ondelete='RESTRICT',onupdate='RESTRICT'),nullable=False)
	theme_id = database.db.Column(database.db.Integer,database.db.ForeignKey('award_theme.id',ondelete='RESTRICT',onupdate='RESTRICT'),nullable=False)
	border_id = database.db.Column(database.db.Integer,database.db.ForeignKey('award_border.id',ondelete='RESTRICT',onupdate='RESTRICT'),nullable=False)
	
	def __init__(self,creator,typeId,message,issuedOn,recipient,background,theme,border):
		self.creator = creator
		self.type_id = typeId
		self.message = message
		self.issuedOn = issuedOn
		self.recipient = recipient
		self.background_id = background
		self.theme_id = theme
		self.border_id = border

	def __repr__(self):
		return '<Award {0} {1} {2}>'.format(self.creator,self.type_id,self.message)

	def check_row(self):
		if self.creator is None and self.recipient is None:
			return True
		
class AwardBackground(database.db.Model):
		id = database.db.Column(database.db.Integer, primary_key=True)
		filename = database.db.Column(database.db.String(32), nullable=False)
		
		background = database.db.relationship('Award', backref='award_background', lazy='dynamic')
		
		def __init__(self,filename):
			self.filename = filename
			
		def __repr__(self):
			return '<AwardBackground {0}>'.format(self.filename)

class AwardTheme(database.db.Model):
		id = database.db.Column(database.db.Integer, primary_key=True)
		theme = database.db.Column(database.db.String(32), nullable=False)
		
		color = database.db.relationship('Award', backref='award_theme', lazy='dynamic')
		
		def __init__(self,theme):
			self.theme = theme
			
		def __repr__(self):
			return '<AwardTheme {0}>'.format(self.theme)

class AwardBorder(database.db.Model):
		id = database.db.Column(database.db.Integer, primary_key=True)
		filename = database.db.Column(database.db.String(32), nullable=False)
		
		border = database.db.relationship('Award', backref='award_border', lazy='dynamic')
		
		def __init__(self,filename):
			self.filename = filename
			
		def __repr__(self):
			return '<AwardBorder {0}>'.format(self.filename)
		
class Employee(database.db.Model):
	id = database.db.Column(database.db.Integer,primary_key=True)
	fname = database.db.Column(database.db.String(32),nullable=False)
	lname = database.db.Column(database.db.String(32),nullable=False)
	email = database.db.Column(database.db.String(32),nullable=False,unique=True)
	
	award = database.db.relationship('Award', backref='employee', lazy='dynamic')
	
	def __init__(self,fname,lname,email):
		self.fname = fname
		self.lname = lname
		self.email = email
			
	def __repr__(self):
		return '<Employee {0} {1} {2}>'.format(self.fname,self.lname,self.email)
	
	
		