'''
This file handles all of the database calls in the application. It uses the
SQL Alchemy library to make SQL calls to the PostGresSQL Database
'''

from __future__ import print_function #debug
import os,sys #sys debug
import boto3
import time
from string import replace
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc
from passlib.hash import argon2
from botocore.exceptions import ClientError
from boto3.s3.transfer import S3Transfer
from random import randint

db = SQLAlchemy()


#Initialize the database with the model files from model.py
class PostgresDatabase(object):
	def __init__(self,clsQuestion,clsAccount,clsAdmin,clsManager,clsAwardType,clsAward,clsAwardBackground,clsAwardTheme,clsEmployee,clsAwardBorder):
		self.Question = clsQuestion
		self.Account = clsAccount
		self.Admin = clsAdmin
		self.Manager = clsManager
		self.AwardType = clsAwardType
		self.Award = clsAward
		self.AwardBackground = clsAwardBackground
		self.AwardTheme = clsAwardTheme
		self.Employee = clsEmployee
		self.AwardBorder = clsAwardBorder
		self.database = db
		
	#retrieve listing of award name colors	
	def getAwardThemes(self):
		themes = {}
		results = db.session.query(self.AwardTheme).all()
		
		for r in results:
			themes[r.id] = r.theme
			
		return themes
	#retrieve list of awards belonging to a certain logged in user
	def getAwards(self,email):
		awards = {}
		creator = self.Manager.query.filter_by(email=email).first()
		results = self.Award.query.filter_by(creator=creator.id).all()
		
		for r in results:
			issuedOnString = r.issuedOn
			issuedOnString = issuedOnString.strftime("%m-%d-%Y")
			recipient = r.employee.fname + ' ' + r.employee.lname
			awards[r.id] = {'id':r.id,'issuedOn':issuedOnString,'recipient':recipient,'type':r.award_type.name}
			
		return awards
	
	#retrieve listing of all the awards in the database
	def getAllAwards(self):
		return db.session.query(self.Award).all()
	
	#return a single award object by id	
	def getAward(self, id):
		return self.Award.query.get(id)
			
	#retrieve listing of award background tile types	
	def getAwardBackgrounds(self):
		backgrounds = {}
		results = db.session.query(self.AwardBackground).all()
		
		for r in results:
			backgrounds[r.id] = r.filename
			
		return backgrounds

	#retrieve listing of award types (employee of the month... etc)	
	def getAwardTypes(self):
		types = {}
		results = db.session.query(self.AwardType).all()
		
		for r in results:
			types[r.id] = r.name
			
		return types

	#retrieve the available security questions for the account creation page	
	def getQuestions(self):
		questions = {}
		results = db.session.query(self.Question).all()
		
		for r in results:
			questions[r.id] = r.prompt
			
		return questions

	#download the user signature file from the Amazon s3 bucket	
	def downloadUserSig(self,email):
		bucket = os.environ.get('S3_BUCKET_NAME')
		
		filename = replace(email,'@','_')
		filename = replace(filename,'.','_')
		filename += '_sig.png'

		client = boto3.client('s3')
		
		try:
			client.download_file(bucket, filename, filename)
		except ClientError as e:
			print(e.response['Error']['Message'],file=sys.stderr)
			return None
		except IOError as e:
			print(e,file=sys.stderr)
			return None
		return True
	
	#delete the user signature file from the Amazon s3 bucket
	def deleteUserSig(self, filename):
		bucket = os.environ.get('S3_BUCKET_NAME')
		client = boto3.client('s3')
		try:
			client.delete_object(Bucket=bucket, Key=filename)
		except ClientError as e:
			print(e.response['Error']['Message'],file=sys.stderr)
			return None
		except IOError as e:
			print(e,file=sys.stderr)
			return None
		return True	

	#get pertinent information about logged in user	
	def getUserDetails(self,email):
		user = self.Manager.query.filter_by(email=email).first()
		
		if user is None:
			return None
			
		self.downloadUserSig(email)
		
		details = {
		'id':user.id,
		'account':user.account.id,
		'fname':user.fname,
		'lname':user.lname,
		'email':user.email,
		'title':user.title,
		'question1':user.account.q1,
		'question2':user.account.q2,
		'answer1':user.account.answer1,
		'answer2':user.account.answer2,
		'signature':user.signature}
		
		return details
	
	#retrieve a listing of all users	
	def getUsers(self):
		managers = {}
		results = self.Manager.query.order_by(asc(self.Manager.lname)).all()
		
		for r in results:
			createdOnString = r.account.created
			createdOnString = createdOnString.strftime("%m-%d-%Y")
			user = r.fname + ' ' + r.lname
			
			managers[r.id] = {'id':r.id,'createdOn':createdOnString,'title':r.title,'user':user, 'useremail': r.email}
			
		return managers
	
	#retrieve a single user
	def getUser(self, id):
		return self.Manager.query.get(id)
	
	#retrieve a listing of all the admins
	def getAdmins(self, email):
		admins = {}
		results = self.Admin.query.filter(self.Admin.email != email, self.Admin.email != 'root@admin.com').all()
		for r in results:
			createdOnString = r.account.created
			createdOnString = createdOnString.strftime("%m-%d-%Y")
			admin = r.fname + ' ' + r.lname
			admins[r.id] = {'id':r.id, 'createdOn': createdOnString, 'admin':admin, 'adminEmail': r.email}
		return admins
	
	#retrieve a single admin user
	def getAdmin(self, id):
		return self.Admin.query.get(id)
	
	#get pertinent details about logged in admin
	def getAdminDetails(self,email):
		admin = self.Admin.query.filter_by(email=email).first()
		
		if admin is None:
			return None
		
		details = {
		'id':admin.id,
		'account':admin.account.id,
		'email':admin.email,
		'fname':admin.fname,
		'lname':admin.lname,
		'question1':admin.account.q1,
		'question2':admin.account.q2,
		'answer1':admin.account.answer1,
		'answer2':admin.account.answer2}
		
		return details
	
	#log specific user into the system
	def login(self,payload):
		email = payload['userName']
		pword = payload['password']
		type = payload['account-type']
		
		if type == 'admin':
			admin = self.Admin.query.filter_by(email=email).first()
			if admin is None:
				return {'status':404,'account':admin,'message':'The provided email is not linked to an existing account.'}
			else:
				password = argon2.verify(pword,admin.account.pword)
				if password == True:
					return {'status':200,'account':admin.account,'message':'Login successful.'} 
				else:
					return {'status':404,'account':admin.account,'message':'An incorrect password was provided.'}
				
		if type == 'user':
			user = self.Manager.query.filter_by(email=email).first()
			if user is None:
				return {'status':404,'account':user,'message':'The provided email is not linked to an existing account.'}
			else:
				password = argon2.verify(pword,user.account.pword)
				if password == True:
					return {'status':200,'account':user.account,'message':'Login successful.'}
				else:
					return {'status':404,'account':user.account,'message':'An incorrect password was provided.'}
				
		return {'status':400,'account':None,'message':'An invalid account type was given.'}
		
	#add new user account to database	
	def createAccount(self,payload):
		fname = payload['firstName']
		lname = payload['lastName']
		email = payload['email']
		title = payload['jobTitle']
		sign = payload['signature']
		pword = argon2.using(rounds=4).hash(payload['password'])
		quest1 = int(payload['security-question-1'])
		quest2 = int(payload['security-question-2'])
		answ1 = payload['security-answer-1']
		answ2 = payload['security-answer-2']
		created = datetime.now()
		
		account = self.Account(pword,quest1,quest2,answ1,answ2,created)
		manager = self.Manager(account,title,fname,lname,sign,email)
			
		return [account,manager]
	
	# add new admin account to the database
	def createAdminAccount(self,payload):
		fname = payload['firstName']
		lname = payload['lastName']
		email = payload['email']
		pword = argon2.using(rounds=4).hash(payload['password'])
		quest1 = int(payload['security-question-1'])
		quest2 = int(payload['security-question-2'])
		answ1 = payload['security-answer-1']
		answ2 = payload['security-answer-2']
		created = datetime.now()
		
		account = self.Account(pword,quest1,quest2,answ1,answ2,created)
		admin = self.Admin(account,email,fname,lname)
			
		return [account,admin]

	# update non-admin account information in the database	
	def updateAccount(self,payload,email):
		user = self.Manager.query.filter_by(email=email).first()
		
		#update signature file if email was changed
		if (user.email != payload['email'] and user.signature == payload['signature']):
			sigFilename = payload['email']
			sigFilename = replace(sigFilename,'@','_')
			sigFilename = replace(sigFilename,'.','_')
			sigFilename += '_sig.png'
			oldFilename = user.signature
			oldFilename = oldFilename.replace('https://camelopardalis-assets.s3.amazonaws.com/',"")
			bucket = os.environ.get('S3_BUCKET_NAME')
			s3 = boto3.resource('s3')
			s3.Object(bucket,sigFilename).copy_from(CopySource={'Bucket':bucket, 'Key':oldFilename})
			s3.Object(bucket,oldFilename).delete()
			tempSig = payload['signature']
			tempSig = tempSig.replace(oldFilename, sigFilename)
			user.signature = tempSig
		else:
			user.signature = payload['signature']
		
		user.fname = payload['firstName']
		user.lname = payload['lastName']
		user.email = payload['email']
		user.title = payload['jobTitle']

		
		try:
			db.session.commit()
		except IntegrityError:
			db.session.rollback()
			return False
			
		return True
	
	# update employee information in the database	
	def updateEmployee(self,payload):
		employee = self.Employee.query.get(int(payload['emp-id']))
		
		employee.fname = payload['first-name']
		employee.lname = payload['last-name']
		employee.email = payload['emp-email']
		
		try:
			db.session.commit()
		except IntegrityError:
			print(e,file=sys.stderr)
			sys.stdout.flush()
			db.session.rollback()
			return False
			
		return True
	
	#update the admin account details in database
	def updateAdminAccount(self,payload,email):
		admin = self.Admin.query.filter_by(email=email).first()
		
		admin.fname = payload['firstName']
		admin.lname = payload['lastName']
		admin.email = payload['email']
		
		try:
			db.session.commit()
		except IntegrityError:
			print(e,file=sys.stderr)
			sys.stdout.flush()
			db.session.rollback()
			return False
			
		return True

	# add a new award to the database from user submittal	
	def createAward(self,payload,email):
		creator = self.Manager.query.filter_by(email=email).first()
		awardType = self.AwardType.query.get(payload['type'])

		if creator is None or awardType is None:
			return None
			
		creatorId = creator.id
		typeId = awardType.id
		message = payload['message']
		issuedOn = payload['send-time']
		recipient = int(payload['employee-to-get-award'])
		background = int(payload['background'])
		theme = int(payload['theme'])
		border = int(payload['border'])
		
		award = self.Award(creatorId,typeId,message,issuedOn,recipient,background,theme,border)
			
		return award
	
	# add a new employee to the database
	def createEmployee(self,payload):

		fname = payload['first-name']
		lname = payload['last-name']
		email = payload['emp-email']
		
		employee = self.Employee(fname,lname,email)
			
		return employee

	# saves all object files retrieved by other calls to the database	
	def save(self,obj):
		try:
			if type(obj) is list:
				db.session.add_all(obj)
			else:
				db.session.add(obj)
				
			db.session.commit()
		except IntegrityError as e:
			print(e,file=sys.stderr)
			sys.stdout.flush()
			db.session.rollback()
			return False
			
		return True
	
	# deletes all object files retrieved by other calls to the database	
	def remove(self,obj):
		try:
			db.session.delete(obj)
			db.session.commit()
		except IntegrityError as e:
			print(e,file=sys.stderr)
			sys.stdout.flush()
			db.session.rollback()
			return False
			
		return True
	
	# retrieves a single account from database
	def getAccount(self,id):
		return self.Account.query.get(id)
	
	# sets logged in user to authenticated
	def setAuthenticated(self,account,val):		
		try:
			account.authenticated = val
			db.session.add(account)
			db.session.commit()
		except IntegrityError as e:
			print(e,file=sys.stderr)
			sys.stdout.flush()
			db.session.rollback()
			return False
			
		return True

	# retrieves a list of employees for create award page
	def getEmployees(self,req):
		if req['lname'] != "":
			employees = {}
			results = self.Employee.query.filter(self.Employee.lname.ilike('%' + req['lname'] + '%')).all()
				
			for r in results:
				employees[r.id] = {'id':r.id,'fname':r.fname,'lname':r.lname,'email':r.email}
			
			employees['status'] = 200
			return employees
		else:
			return {'status':404,'message':'The search returned no results.'} 
	
	# returns a single emplyoee by id
	def getEmployee(self, id):
		return self.Employee.query.get(id)
	
	# retrieves a list of all employees for employee listing page
	def getAllEmployees(self):
		employees = {}
		results = self.Employee.query.order_by(asc(self.Employee.lname)).all()
		
		for r in results:
			employee = r.fname + ' ' + r.lname
			employees[r.id] = {'id':r.id,'employee':employee, 'empemail': r.email}		
		return employees
	
	# gets account verification code for password recovery route
	def genVerificationCode(self,id):
		account = self.Account.query.get(id)
		code = randint(10000,99999)
		
		try:
			account.code = code
			db.session.add(account)
			db.session.commit()
		except IntegrityError as e:
			print(e,file=sys.stderr)
			sys.stdout.flush()
			db.session.rollback()
			return None
			
		return code
	
	#changes account password based on submitted password in recovery form
	def resetPasswordByEmail(self,payload):
		response = {'status':200,'message':'Your password has been reset.'}
		
		if payload['account-type'] == 'user':
			user = self.getUserDetails(payload['userName'])
		elif payload['account-type'] == 'admin':
			user = self.getAdminDetails(payload['userName'])
			
		if user is None:
			response = {'status':404,'message':'There is no account linked to that email address.'}
			return response
			
		account = self.Account.query.get(user['account'])

		if int(payload['reset-code']) != account.code:
			response = {'status':400,'message':'Incorrect verification number. You will have to get another code.'}
		else:	
			account.pword = argon2.using(rounds=4).hash(payload['password'])
			
		account.code = None
		
		try:
			db.session.commit()
		except IntegrityError:
			response = {'status':500,'message':'Unable to reset password.'}
			print(e,file=sys.stderr)
			sys.stdout.flush()
			db.session.rollback()
			return response
			
		return response 
	
	# checks to see that security questions are answered correctly in password retrieval
	def verifyAnswers(self,payload):
		accountType = 'user'
		details = self.getUserDetails(payload['email'])
		
		if details is None:
			accountType = 'admin'
			details = self.getAdminDetails(payload['email'])
			
			if details is None:
				response = {'status':404, 'message':'The provided email is not linked to an account.'}
				return response
		
		if details['answer1'] != payload['answer1'] or details['answer2'] != payload['answer2']:
			response = {'status':400, 'message':'One or more of the given security question answers are incorrect.'}
			return response
			
		response = {'status':200, 'message':'The answers to your security questions have been verified.','account':details['account']}

		return response
			
	#changes password based on submitted password during password recovery process	
	def resetPasswordByQuestions(self,payload):
		account = self.Account.query.get(payload['account'])
		account.pword = argon2.using(rounds=4).hash(payload['password']) 
			
		try:
			db.session.commit()
		except IntegrityError:
			print(e,file=sys.stderr)
			sys.stdout.flush()
			db.session.rollback()
			return False
			
		return True
	
	#retrieve user by email
	def findUser(self,email):
		user = self.Manager.query.filter_by(email=email).first()
		
		if user is None:
			user = self.Admin.query.filter_by(email=email).first()
			if user is None:
				return {'status':404,'message':'The email you provided is not linked to an account.','role':None,'email':None}
			else:
				return {'status':200,'message':'User found.','role':'admin','email':email}
		
		return {'status':200,'message':'User found.','role':'user','email':email}	
	
	# add a new award type to database
	def addAwardType(self,payload):
		types = self.getAwardTypes()
		
		if payload['awardType'] not in types.values():
			type = self.AwardType(payload['awardType'])
			return self.save(type)
		
		return False
	
