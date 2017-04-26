'''
Title: Employee Recognition System
Authors: Sarah Cawley, Ryan Cosby, and Conrad Lewin
Oregon State University Capstone Course
Description: This is the main routing file used to handle all of the server side routing calls for our 
employee recognition system. The application is used to deliver award recognition emails to employee
recipients. Admin users are able to monitor users and the number of awards being delivered to employees.
'''

from __future__ import print_function #debug
import os
import logging
import json, boto3
from handlers.LaTex import award as ah
from handlers.Database import database
from handlers.Database import models
from handlers.Email import email
from handlers.Report import report
from string import replace
from flask import Flask, render_template, send_file, abort, request, redirect, url_for, jsonify, session, Response, flash
from flask_cors import CORS, cross_origin
from flask_login import LoginManager, login_required, current_user, login_user, logout_user

#"constants" used to change the color of messages flashed to the 
#screen after CRUD operations performed by the user
ERROR = 'red'
SUCCESS = 'green'

#init Flask framework
app = Flask('app',template_folder='./templates',static_folder='./static')
app.secret_key = os.environ['SECRET_KEY']

#init CORS
CORS(app)

#connect database to application
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
database.db.init_app(app)

#init Flask login functionality
loginManager = LoginManager()
loginManager.init_app(app)


#init object that will handle database operations
alchemist = database.PostgresDatabase(
models.Question,
models.Account,
models.Admin,
models.Manager,
models.AwardType,
models.Award,
models.AwardBackground,
models.AwardTheme,
models.Employee,
models.AwardBorder)

#init object that will handle email functionality
emailer = email.Emailer()

#init object that will handle report data retrieval
reporter = report.Reporter(alchemist.database)

#landing page route
@app.route('/')
def renderIndex():
	#render the landing page
	return render_template('index.html')


#login page route
@app.route('/login',methods=['GET','POST'])
def renderLogin():
	'''
	GET: render login page
	POST: using data provided by the login form, validate the user's credentials and
	display a status message regarding the state of the login. Relevant session variables
	are saved (email, role, name and title(if regular user)).
	'''
	
	if request.method == 'GET':			
		return render_template('login.html')
	
	if request.method == 'POST':
		payload = request.form
		response = alchemist.login(payload)

		if response['status'] != 200:
			flash(response['message'],ERROR)
			return render_template('login.html')
		
		session['email'] = payload['userName']
		session['role'] = payload['account-type']

		status = alchemist.setAuthenticated(response['account'],True)

		if status == True:
			login_user(response['account'])
			
			if payload['account-type'] == 'admin':
				session['name'] = '{0} {1}'.format(response['account'].admin.fname,response['account'].admin.lname)
				return redirect(url_for('renderAdmin'))
			else:
				session['name'] = '{0} {1}'.format(response['account'].manager.fname,response['account'].manager.lname)
				session['title'] = response['account'].manager.title
				return redirect(url_for('renderUser'))			
		else:
			abort(401)
			

#logout page route
@app.route('/logout')
def renderLogout():
	'''logout the user and render the logout page'''
	
	alchemist.setAuthenticated(current_user,False)
	logout_user()
	return render_template('logout.html')


#admin portal route	(admin user must be logged in to access this page)
@app.route('/admin')
@login_required
def renderAdmin():
	'''render the admin portal'''
	
	if session['role'] == 'admin':
		return render_template('admin.html', username=session['name'],email=session['email'],updateRoute='update-admin-account')
	else:
		abort(401)

# admin listing rout		
@app.route('/admins')
@login_required
def renderAdmins():	
	'''renders a table of all of the admins in the system'''
	if session['role'] == 'admin':
		admins = alchemist.getAdmins(session['email'])
		return render_template('admins-list.html', admins=admins, username=session['name'], email=session['email'],updateRoute='update-admin-account')
	else:
		abort(401)

		
#regular user portal route (regular user must be logged in to access this page)
@app.route('/user')
@login_required
def renderUser():
	'''render the user portal'''
	
	if session['role'] == 'user':
		return render_template('user.html',username=session['name'],email=session['email'])
	else:
		abort(401)


#update account route (regular user must be logged in to access this page)
@app.route('/update-account',methods=['GET','POST'])
@login_required
def renderUpdateAccount():
	'''
	after ensuring a regular user is accessing the route...
	GET: retrieve the logged in user's account details from the database and then render the page
	POST: get form data and update the user's account in the database. save the updated user details
	in the session dictionary and display a status message
	'''
	
	if session['role'] == 'user':
		if request.method == 'GET':
			details = alchemist.getUserDetails(session['email'])
			
			if details is None:
				abort(500)
				
			return render_template('update-account.html',username=session['name'], email=session['email'], details=details)
			
		if request.method == 'POST':
			payload = request.form
			status = alchemist.updateAccount(payload,session['email'])
			
			if status == False:
				flash('Unable to update account. Either the email provided is already linked to an account or there was a server error. Please, try again.', ERROR)
				return redirect(url_for('renderUpdateAccount'))
				
			session['name'] = '{0} {1}'.format(payload['firstName'],payload['lastName'])
			session['email'] = payload['email']
			session['title'] = payload['jobTitle']
			##flash('Account was successfully updated.',SUCCESS) <---this is not displaying correctly
			return redirect(url_for('renderUser'))
	else:
		abort(401)
	

#create award route (regular user must be logged in to access this page)
@app.route('/create')
@login_required
def renderCreate():
	'''
	after ensuring a regular user is accessing the route, retrieve award assets from the database 
	and then render the page.
	'''
	
	if session['role'] == 'user':
		awardBackgrounds = alchemist.getAwardBackgrounds()
		awardThemes = alchemist.getAwardThemes()
		awardTypes = alchemist.getAwardTypes()
		return render_template('create.html', username=session['name'], email=session['email'], awardBackgrounds=awardBackgrounds, awardThemes=awardThemes, awardTypes=awardTypes)
	else:
		abort(401)


#create new regular user account route		
@app.route('/new-account',methods=['GET','POST'])
def renderNewAccount():
	'''
	GET: get the list of available security questions from the database, then render the page
	POST: get form data, use that data to insert account information into the database and
	then display a status message before rendering the login (if successful) or new account
	page (if unsuccessful). 
	'''
	
	if request.method == 'GET':
		questions = alchemist.getQuestions()
		return render_template('new-account.html',questions=questions)
	
	if request.method == 'POST':
		payload = request.form
		account = alchemist.createAccount(payload)
		status = alchemist.save(account)
		
		if status == False:
			flash('Unable to create account. The email provided is already linked to an account.',ERROR)
			return redirect(url_for('renderNewAccount'))
		
		flash('Account created.',SUCCESS)
		return redirect(url_for('renderLogin'))

#create a new admin account route		
@app.route('/new-admin-account',methods=['GET','POST'])
def renderNewAdminAccount():
	'''
	GET: renders the new admin account submittal form
	POST: get form data, use that data to insert account information into the database and
	then display a status message before rendering the login (if successful) or new account
	page (if unsuccessful)
	'''
	if request.method == 'GET':
		questions = alchemist.getQuestions()
		return render_template('new-admin-account.html',questions=questions, username=session['name'], email=session['email'],updateRoute='update-admin-account')
	
	if request.method == 'POST':
		payload = request.form
		account = alchemist.createAdminAccount(payload)
		status = alchemist.save(account)
		
		if status == False:
			flash('Unable to create admin account. The email provided is already linked to an account.',ERROR)
			return redirect(url_for('renderNewAdminAccount', username=session['name'], email=session['email']))###,updateRoute='update-admin-account' maybe
		
		flash('Admin account created.',SUCCESS)
		return redirect(url_for('renderAdmin', username=session['name'], email=session['email']))

#update current logged in admin account route here		
@app.route('/update-admin-account/',methods=['GET','POST'])
@login_required
def renderUpdateAdminAccount():	
	'''
	GET: renders the update admin account submittal form
	POST: get form data, use that data to update account information into the database and
	then display a status message before rendering the login (if successful) or new account
	page (if unsuccessful)
	'''
	if session['role'] == 'admin':
		if request.method == 'GET':
			details = alchemist.getAdminDetails(session['email'])
			
			if details is None:
				abort(500)
				
			return render_template('update-admin-account.html',username=session['name'], email=session['email'], details=details,updateRoute='update-admin-account')
			
		if request.method == 'POST':
			payload = request.form
			status = alchemist.updateAdminAccount(payload,session['email'])
			
			if status == False:
				flash('Unable to update admin account. Either the email provided is already linked to an account or there was a server error. Please, try again.', ERROR)
				return redirect(url_for('renderUpdateAdminAccount', username=session['name'], email=session['email'], details=details))
				
			session['email'] = payload['email']
			session['name'] = '{0} {1}'.format(payload['firstName'],payload['lastName'])
			flash('Admin account was successfully updated.',SUCCESS)
			return redirect(url_for('renderAdmins'))
	else:
		abort(401)

#update other admin account route		
@app.route('/update-other-admin-account/',methods=['GET','POST'])
@login_required
def renderUpdateOtherAdminAccount():
	'''
	GET: renders the update admin account submittal form
	POST: get form data, use that data to update account information into the database and
	then display a status message before rendering the login (if successful) or new account
	page (if unsuccessful)
	'''
	if session['role'] == 'admin':
		if request.method == 'GET':
			session['admin-email'] = request.args.get('adminemail')
			details = alchemist.getAdminDetails(session['admin-email'])
			
			if details is None:
				abort(500)
				
			return render_template('update-other-admin-account.html',username=session['name'], email=session['email'], details=details, updateRoute='update-admin-account')
		
	if request.method == 'POST':
		payload = request.form
		status = alchemist.updateAdminAccount(payload,session['admin-email'])		
		if status == False:
			flash('Unable to update admin account. Either the email provided is already linked to an account or there was a server error. Please, try again.', ERROR)
			return redirect(url_for('renderOtherUpdateAdminAccount', username=session['name'], email=session['email'], details=details, updateRoute='update-admin-account'))
			
		flash('Admin account was successfully updated.',SUCCESS)
		return redirect(url_for('renderAdmins'))
	else:
		abort(401)

#delete admin account route		
@app.route('/remove-admin/')
def removeAdminUser():
	'''
	Finds the selected admin account from the admin listing table and deletes the account. 
	The admin list is rendered again to show the account has been removed
	'''
	adminID = request.args.get('admin')
	admin = alchemist.getAdmin(adminID)
	status = alchemist.remove(admin.account)
	admins = alchemist.getAdmins(session['email'])
	if status == False:
		flash('Unable to remove admin. System Error.', ERROR)
		return redirect(url_for('renderAdmins', admins=admins, username=session['name'], email=session['email']))
	flash('Admin deleted.', SUCCESS)
	return redirect(url_for('renderAdmins', admins=admins, username=session['name'], email=session['email']))
		
#create a new standard user account from admin login	
@app.route('/new-manager-account',methods=['GET','POST'])
@login_required
def renderNewUserAccount():
	'''
	GET: renders the new user account submittal form
	POST: get form data, use that data to insert account information into the database and
	then display a status message before rendering the login (if successful) or new account
	page (if unsuccessful)
	'''
	if session['role'] == 'admin':
		if request.method == 'GET':
			questions = alchemist.getQuestions()
			return render_template('new-manager-account.html',questions=questions, username=session['name'], email=session['email'],updateRoute='update-admin-account')
		
		if request.method == 'POST':
			payload = request.form
			account = alchemist.createAccount(payload)
			status = alchemist.save(account)
			
			if status == False:
				flash('Unable to create account. The email provided is already linked to an account.',ERROR)
				return redirect(url_for('renderNewUserAccount', username=session['name'], email=session['email']))
			
			flash('Account created.',SUCCESS)
			return redirect(url_for('renderAdmin', username=session['name'], email=session['email']))
	else:
		abort(401)
		
# update standard user account from admin login
@app.route('/update-manager-account/',methods=['GET','POST'])
@login_required
def renderUpdateUserAccount():
	'''
	GET: renders the update account submittal form
	POST: get form data, use that data to update account information into the database and
	then display a status message before rendering the login (if successful) or update account
	page (if unsuccessful)
	'''	
	if session['role'] == 'admin':
		if request.method == 'GET':
			session['manager-email'] = request.args.get('usremail')
			details = alchemist.getUserDetails(session['manager-email'])
			
			if details is None:
				abort(500)
				
			return render_template('update-manager-account.html',username=session['name'], email=session['email'], details=details,updateRoute='update-admin-account')
			
		if request.method == 'POST':
			payload = request.form
			status = alchemist.updateAccount(payload,session['manager-email'])
			
			if status == False:
				flash('Unable to update account. Either the email provided is already linked to an account or there was a server error. Please, try again.', ERROR)
				return redirect(url_for('renderUpdateUserAccount', username=session['name'], email=session['email'], details=details))
				
			flash('Account was successfully updated.',SUCCESS)
			return redirect(url_for('renderUsers'))
	else:
		abort(401)

#add new employee route		
@app.route('/new-employee', methods=['GET','POST'])
@login_required
def addNewEmployee():
	'''
	GET: renders the new employee submittal form
	POST: get form data, use that data to insert employee information into the database and
	then display a status message before rendering the login (if successful) or new employee
	page (if unsuccessful)
	'''
	if request.method == 'GET':
		return render_template('new-employee.html', username=session['name'], email=session['email'], updateRoute='update-admin-account')
	
	if request.method == 'POST':
		payload = request.form
		employee = alchemist.createEmployee(payload)
		status = alchemist.save(employee)
		
		if status == False:
			flash('Unable to create employee. System Error.',ERROR)
			return redirect(url_for('addNewEmployee', username=session['name'], email=session['email']))
		
	flash('Employee Added: ' + employee.fname +' '+ employee.lname ,SUCCESS)
	return redirect(url_for('renderEmployees', username=session['name'], email=session['email']))

#update employee info route	
@app.route('/update-employee/',methods=['GET','POST'])
@login_required
def renderUpdateEmployee():
	'''
	GET: renders the update employee submittal form
	POST: get form data, use that data to update employee information into the database and
	then display a status message before rendering the login (if successful) or update employee
	page (if unsuccessful)
	'''
	if session['role'] == 'admin':
		if request.method == 'GET':
			employeeID = request.args.get('employee')
			employee = alchemist.getEmployee(employeeID)
			
			if employee is None:
				abort(500)
				
			return render_template('update-employee.html',username=session['name'], email=session['email'], employee=employee,updateRoute='update-admin-account')
			
		if request.method == 'POST':
			payload = request.form
			status = alchemist.updateEmployee(payload)
			
			if status == False:
				flash('Unable to employee information. System Error', ERROR)
				return redirect(url_for('renderUpdateEmployee', username=session['name'], email=session['email']))
				
			flash('Employee information was successfully updated',SUCCESS)
			return redirect(url_for('renderEmployees',username=session['name'], email=session['email']))
	else:
		abort(401)	


#view awards route (regular user must be logged in to access this page)
@app.route('/awards')
@login_required
def renderAwards():
	'''
	after ensuring a regular user is accessing the route, get all awards that user has 
	created from the database and then render the page.
	'''
	
	if session['role'] == 'user':
		awards = alchemist.getAwards(session['email'])
		return render_template('user-awards-list.html', awards=awards, username=session['name'], email=session['email'])
	else:
		abort(401)
	
#route to view listing of non-admin users	
@app.route('/users')
@login_required
def renderUsers():
	'''
	after ensuring an admin user is accessing the route, get all users in the database
	and render the table in the page.
	'''
	if session['role'] == 'admin':
		users = alchemist.getUsers()
		return render_template('users-list.html', users=users, username=session['name'], email=session['email'],updateRoute='update-admin-account')
	else:
		abort(401)
	

#remove awards route
@app.route('/remove-award/')
def removeAward():
	'''
	get the id of the award to be removed (retrieved from the page),
	find that award in the database, remove it and then display a status message.
	retrieve all remaining awards from the database so that they can be displayed
	once the page is reloaded.
	'''
	
	awardID = request.args.get('awd')
	award = alchemist.getAward(awardID)
	status = alchemist.remove(award)
	awards = alchemist.getAwards(session['email'])
	if status == False:
		flash('Unable to remove award. System Error.', ERROR)
		return redirect(url_for('renderAwards', awards=awards, username=session['name'], email=session['email']))
	flash('Award record deleted', SUCCESS)
	return redirect(url_for('renderAwards', awards=awards, username=session['name'], email=session['email']))
	
	
#remove user route
@app.route('/remove-user/')
def removeUser():
	'''
	get the id of the user to be removed (retrieved from the page),
	find that user in the database, remove them (as well as their 
	signature image from the s3 bucket) and then display a status message.
	retrieve all remaining users from the database so that they can be displayed
	once the page is reloaded.
	'''
	
	userID = request.args.get('usr')
	user = alchemist.getUser(userID)
	users = alchemist.getUsers()
	
	sigFilename = user.signature
	sigFilename = sigFilename.replace('https://camelopardalis-assets.s3.amazonaws.com/',"")
	
	if alchemist.remove(user.account) == False:
		flash('Unable to remove user. System Error.', ERROR)
		return redirect(url_for('renderUsers', users=users, username=session['name'], email=session['email']))
	else:
		alchemist.deleteUserSig(sigFilename)

	awards = alchemist.getAllAwards()
	if awards is not None:
		for a in awards:
			if a.check_row() == True:
				alchemist.remove(a)
	
	flash('User deleted.', SUCCESS)
	return redirect(url_for('renderUsers', users=users, username=session['name'], email=session['email']))
		

#list/add award types route (admin user must be logged in to access this page)
@app.route('/award-types',methods=['GET','POST'])
@login_required
def renderAwardTypes():
	'''
	after ensuring an admin user is accessing the route...
	GET: get all available award types from database and render the page
	POST: get form data, add that data into the database and then display a status message
	before reloading the page.
	'''
	
	if session['role'] == 'admin':
		if request.method == 'GET':
			types = alchemist.getAwardTypes()
			return render_template('add-award-type.html',types=types,username=session['name'], email=session['email'],updateRoute='update-admin-account')
		
		if request.method == 'POST':
			if alchemist.addAwardType(request.form) == False:
				flash('Unable to create award type. Make sure your are not trying to create a duplicate type.',ERROR)
			else:
				flash('New award type created.',SUCCESS)
				
			return redirect(url_for('renderAwardTypes'))
	else:
		abort(401)


#display reports route (admin user must be logged in to access this route)
@app.route('/reports',methods=['GET','POST'])
@login_required
def renderReports():
	''' 
	after ensuring an admin user is accessing the route...
	GET: render the page
	POST: receive a json request object containing a report code from a button on the page. 
	retrieve the appropriate data needed to generate the selected report and then return that data
	as a json object
	'''
	
	if session['role'] == 'admin':
		if request.method == 'GET':
			return render_template('reports.html',username=session['name'], email=session['email'],updateRoute='update-admin-account')
		
		if request.method == 'POST':
			if request.json:
				payload = request.get_json()
				
				if payload['report'] == '1':
					response = reporter.getAllAwards()
				elif payload['report'] == '2':
					response = reporter.getAwardsByManager()
				elif payload['report'] == '3':
					response = reporter.getAwardsByEmployee()
				else:
					abort(400)
					
				return jsonify(response)
					
			else:
				abort(400)
	else:
		abort(401)

#internal route used to submit signature file to Amazon S3 service
#Source: https://devcenter.heroku.com/articles/s3-upload-python
@app.route('/sign_s3/')
def sign_s3():
	S3_BUCKET = os.environ.get('S3_BUCKET_NAME')

	file_name = request.args.get('file_name')
	file_type = request.args.get('file_type')

	s3 = boto3.client('s3')

	presigned_post = s3.generate_presigned_post(
		Bucket = S3_BUCKET,
		Key = file_name,
		Fields = {"acl": "public-read", "Content-Type": file_type},
		Conditions = [
			{"acl": "public-read"},
			{"Content-Type": file_type}
		],
		ExpiresIn = 3600
	)
	return json.dumps({
		'data': presigned_post,
		'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, file_name)
	})

#internal route used to delete signature files from the system when user accoutns are deleted	
@app.route('/delete_s3/')
def delete_s3():
	file_name = request.args.get('file_name')
	print (file_name)
	alchemist.deleteUserSig(file_name);
	return json.dumps({'status': "success"})
	

#forgot password route
@app.route('/password')
def renderPassword():
	'''render forgot password page'''
	
	return render_template('password.html')

	
#award pdf generation route (a regular user must be logged in to make post requests to the this route)
@app.route('/latex', methods=['POST'])
@login_required
def renderPDF():
	#get form data and insert that data into the database
	payload = request.form
	award = alchemist.createAward(payload, session['email'])
	
	if award is None:
		abort(404)
		
	status = alchemist.save(award)
			
	if status == False:
		abort(500)
	#----------------------------------------------------
	
	#form the filename used to retrieve signature from the s3 bucket
	sigFile = session['email']
	sigFile = replace(sigFile,'@','_')
	sigFile = replace(sigFile,'.','_')
	sigFile += '_sig.png'
	
	#download the signature image from the bucket
	alchemist.downloadUserSig(session['email'])
	
	#LaTex code used to generate the two different award borders
	if payload['border'] == '1':
		border = r'''{\border \char113} % up left
				{\border \char109} % up
				{\border \char112} % up right
				{\border \char108} % left 
				{\border \char110} % right
				{\border \char114} % lower left
				{\border \char111} % bottom
				{\border \char115} % lower right'''
	else:
		border = r'''{\border \char005} % up left
				{\border \char001} % up
				{\border \char004} % up right
				{\border \char002} % left 
				{\border \char000} % right
				{\border \char006} % lower left
				{\border \char003} % bottom
				{\border \char007} % lower right'''
	
	#form award details to be inserted into the LaTex template
	filename = 'award'
	
	awardDate = award.issuedOn
	awardDateString = awardDate.strftime("%m-%d-%Y")

	awdDetails = {
	'background':'static/images/' + award.award_background.filename,
	'border': border,
	'color':award.award_theme.theme,
	'logo':'static/images/gateway.png',
	'company':'Gateway Mapping, Inc.',
	'message': award.message,
	'type': award.award_type.name,
	'employee':award.employee.fname + ' ' + award.employee.lname,
	'admin':session['name'],
	'adminTitle':session['title'],
	'signature':sigFile,
	'granted':awardDateString}
	#------------------------------------------------------------
	
	#generate the pdf file
	employeeAward = ah.Award(awdDetails,filename)
	pdf = employeeAward.genAward()
	
	#if pdf was successfully generated...
	if pdf is not None:
		#if the user elects to preview the award, then remove the award from the database
		#download the pdf to the user's local machine
		if 'preview-btn' in payload:
			alchemist.remove(award)
			return send_file(pdf, as_attachment=True)
		#otherwise, email the pdf to the employee specified in the form
		elif 'email-btn' in payload:				
			sender = session['email']
			recipient = award.employee.email
			response = emailer.sendAward(sender,recipient,pdf)
			
			#display a status message
			if response.status_code != 200 and response.status_code != 202:
				flash('An error occured and the email was not sent. Please, try again.',ERROR)
			else:
				flash('The award has been emailed.',SUCCESS)
				
			return redirect(url_for('renderCreate'))
	#otherwise, remove the award from the database and display an error
	else:
		alchemist.remove(award)
		abort(500)

#get a list of employees route used for create award page
@app.route('/get-employee',methods=['POST'])
def getEmployees():
	'''
	receives a json request with a string representing all or part of an 
	employee's last name. this data is then used to query the database 
	for all employees with last names matching that string.
	'''
	
	if request.json:
		payload = request.get_json()
		employees = alchemist.getEmployees(payload)
		return jsonify(employees)
	else:
		abort(400)

		
#get a list of employees route used for employee list page for logged in admin		
@app.route('/employees-list')
def renderEmployees():
	if session['role'] == 'admin':
		employees = alchemist.getAllEmployees()
		return render_template('employees-list.html', employees=employees, username=session['name'], email=session['email'],updateRoute='update-admin-account')
	else:
		abort(401)


#remove employee route		
@app.route('/remove-employee/')
def removeEmployee():
	'''
	get the id of the employee to be removed (retrieved from the page),
	find that employee in the database, remove it and then display a status message.
	retrieve all remaining employees from the database so that they can be displayed
	once the page is reloaded. a check is then made to ensure that there are no awards
	in the database that lack both a creator and a recipient. if such an award is found,
	it is removed from the database.
	'''
	
	userID = request.args.get('employee')
	employee = alchemist.getEmployee(userID)
	employees = alchemist.getAllEmployees()
	
	if alchemist.remove(employee) == False:
		flash('Unable to remove employee. System Error.', ERROR)
		return redirect(url_for('renderEmployees', employees=employees, username=session['name'], email=session['email']))
	
	awards = alchemist.getAllAwards()
	if awards is not None:
		for a in awards:
			if a.check_row() == True:
				alchemist.remove(a)
	
	flash('Employee deleted.', SUCCESS)
	return redirect(url_for('renderEmployees', employees=employees, username=session['name'], email=session['email']))


#get account password route
@app.route('/get-password',methods=['POST'])
def getPassword():
	'''
	receive json request containing the email linked to the account requesting a password reset
	and then find that account in the database. if such an account exists, identify its role and
	get the account details, namely the password. extract the reset method from the json request
	and return either the security questions linked to the account or send an email to the account
	holder with a verification code that will enable them to reset their password.
	'''
	
	if request.json:
		payload = request.get_json()
		user = alchemist.findUser(payload['email'])
		
		if user['role'] == None:
			response = {'status':404,'message':'The email you provided is not linked to an account.'}
			return jsonify(response)
			
		if user['role'] == 'user':
			details = alchemist.getUserDetails(payload['email'])	
		elif user['role'] == 'admin':
			details = alchemist.getAdminDetails(payload['email'])
			
		if payload['reset-method'] == 'question':
			response = {'one':str(details['question1']), 'two':str(details['question2']),'status':200}
			return jsonify(response)
		elif payload['reset-method'] == 'email':
			code = alchemist.genVerificationCode(details['account'])
			
			if code is not None:
				response = emailer.sendPasswordReset(payload['email'],code)
			else:
				abort(500)
			
			return jsonify(response)
	else:
		abort(400)


#reset password (via email/verification code) route
@app.route('/reset-password', methods=['GET', 'POST'])
def resetPasswordViaEmail():
	'''
	GET: render reset password page
	POST: get form data, validate verfication code and reset account password, then
	display a status message before rendering the login page (if reset was successful)
	or the reset password page (if unsuccessful).
	'''
	
	if request.method == 'GET':
		return render_template('/reset-password.html')
		
	if request.method == 'POST':
		payload = request.form
		response = alchemist.resetPasswordByEmail(payload)
		
		if response['status'] != 200:
			flash(response['message'],ERROR)
			return redirect(url_for('resetPasswordViaEmail'))
		
		flash(response['message'],SUCCESS)		
		return redirect(url_for('renderLogin'))
		

#reset password by security question route
@app.route('/reset-pass-via-question', methods=['POST'])
def resetPasswordViaQuestion():
	'''
	POST: get form data, validate the answers given for the security questions then
	display a status message before rendering the login page.
	'''
	
	payload = request.form
	status = alchemist.resetPasswordByQuestions(payload)
	
	if status == False:
		abort(500)
	
	flash('Password was reset.',SUCCESS)
	return redirect(url_for('renderLogin'))
		

#validate security questions route
@app.route('/check-questions',methods=['POST'])
def checkQuestions():
	'''
	get json request containing the answers to an account's security questions,
	verify those answers against data in the database and return the status.
	'''
	
	if request.json:
		payload = request.get_json()
		response = alchemist.verifyAnswers(payload)
		
		return jsonify(response)
	else:
		abort(400)


#ensures a user is logged in to the application		
@loginManager.user_loader
def accountLoader(id):
	return alchemist.getAccount(id)

	
@app.route('/jquery')
def jquerytest():
    return render_template('jquery.html')


#handles server errors	
@app.errorhandler(500)
def serverError(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred: ' + str(e), 500


#handles resource not found errors, i.e. when queried data is not found in the database
@app.errorhandler(404)
def resourceNotFoundError(e):
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred: ' + str(e), 400


#handles errors that occur when users access routes they are not authorized to view	
@app.errorhandler(401)
def unauthorizedError(e):
    return '<h1>You are not authorized to access this page.</h1> \
	<p>Please login <a href=/login>here</a></p>', 401


#handles errors that arise when a request is malformed	
@app.errorhandler(400)
def badRequestError(e):
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred: ' + str(e), 400


#main	
if __name__ == "__main__":
    app.run()




