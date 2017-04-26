from __future__ import print_function #debug
import sendgrid
import base64
from sendgrid.helpers.mail import *
import os

#this class provides a blueprint for objects that can 
#handle the application's email functionality
class Emailer(object):

	#link the API key needed to use SendGrid's email services to the object
	def __init__(self):
		self.key = os.environ['SENDGRID_API_KEY']
	
	
	#this function sends an email to a specified recipient containing a pdf of a user created award
	def sendAward(self,sentBy,sendTo,image,sub='Your Award',text='Congrats!'):
		#init email details
		sg = sendgrid.SendGridAPIClient(apikey=self.key)
		sender = Email(sentBy)
		subject = sub
		recepient = Email(sendTo)
		content = Content("text/plain", text)
		
		#attach the pdf to the email
		with open(image,'rb') as file:
			data = file.read()

		encoded = base64.b64encode(data)

		attachment = Attachment()
		attachment.set_content(encoded)
		attachment.set_type("application/pdf")
		attachment.set_filename("award.pdf")
		attachment.set_disposition("attachment")
		attachment.set_content_id("Award")
		
		mail = Mail(sender,subject,recepient,content)
		mail.add_attachment(attachment)
		#--------------------------------------------------
		
		#send the email and return a status code
		response = sg.client.mail.send.post(request_body=mail.get())
		return response
		
	
	#this function sends a password reset email
	def sendPasswordReset(self,sendTo,code):
		#email body
		text = '''
		<p>You have elected to reset your password by email. Below is the verification code you will need to reset your password.<p>
		<p>Verification Code: {0}</p>
		<p>Please, do not respond to this email.'''.format(code)
		
		#form email
		sg = sendgrid.SendGridAPIClient(apikey=self.key)
		sender = Email('help@admin.com')
		subject = 'Employee Awards Password Reset'
		recepient = Email(sendTo)
		content = Content('text/html',text)
		
		#send email and return the status of the operation
		mail = Mail(sender,subject,recepient,content)
		response = sg.client.mail.send.post(request_body=mail.get())
		
		return {'status':response.status_code,'message':'An email has been sent to ' + sendTo + '. Please, check your email and reset your password.'}
		
	
		