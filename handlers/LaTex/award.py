from __future__ import print_function #debug
import os,sys
from subprocess import check_call,CalledProcessError

class Award(object):
	'''
	Serves as the template for award PDFs.
	param awardDetails -> details to be retrieved from a form when creating the award.
		requires a dict object with the following keys: 'background','logo','company','message','title','employee','admin1','admin2','adminTitle1','adminTitle2'
	param saveAs -> the name you want to ascribe to the PDF file. do not include an extension
	'''
	
	def __init__(self,awardDetails,saveAs):
		self.details = awardDetails
		self.filename = saveAs
		self.awardTemplate = r'''
		\documentclass[landscape]{article}
		\usepackage{wallpaper}
		\usepackage{niceframe}
		\usepackage{xcolor}
		\usepackage{ulem}
		\usepackage{graphicx}
		\usepackage{geometry}
		\geometry{tmargin=.5cm,bmargin=.5cm,
		lmargin=.5cm,rmargin=.5cm}
		\usepackage{multicol}
		\setlength{\columnseprule}{0.4pt}
		\columnwidth=0.3\textwidth

		\begin{document}

		\TileWallPaper{4cm}{2cm}{''' + awardDetails['background'] + r'''}

		\centering
		\scalebox{3.0}{\color{green!30!black!60}
		\begin{minipage}{.33\textwidth}
		\font\border=umrandb
		\generalframe
		{\border \char113} % up left
		{\border \char109} % up
		{\border \char112} % up right
		{\border \char108} % left 
		{\border \char110} % right
		{\border \char114} % lower left
		{\border \char111} % bottom
		{\border \char115} % lower right
		{\centering

		\begin{minipage}{.9\textwidth}
		\centering
		\includegraphics[height=0.9cm]{''' + awardDetails['logo'] + r'''}
		\end{minipage}
		\vspace{-8mm}

		\curlyframe[.9\columnwidth]{

		\textcolor{red!10!black!90}
		{\small ''' + awardDetails['company'] + r'''}\\ 
		\textcolor{green!10!black!90}{
		\tiny ''' + awardDetails['message'] + r'''}

		\smallskip

		\textcolor{black}{\large \textsc{''' + awardDetails['type'] + r'''}}

		\vspace{2mm}

		\small
		{\textcolor{black}{
		\uppercase{''' + awardDetails['employee'] + r'''}}}

		\vspace{8mm}

		{\color{blue!40!black}
		\scalebox{.8}{
		\begin{tabular}{ccc}
		\cline{1-1} 
		\cline{3-3}
		\ ''' + awardDetails['admin1'] + r''' & & ''' + awardDetails['admin2'] + r'''\\
		\ ''' + awardDetails['adminTitle1'] + r''' & & ''' + awardDetails['adminTitle2'] + r'''\\
		\end{tabular}
		}}}}
		\end{minipage}
		}
		\end{document}
		'''
		
	def __genTexFile(self,filename):
		'''
		generates a .tex file based on the awardTemplate property. errors will be logged in a log.txt.
		if successful the .tex file name is returned, otherwise None is returned
		'''
		
		texFile = filename + '.tex'
		try:
			with open(texFile,'w') as file:
				file.write(self.awardTemplate)
		except IOError as e:
			print('Unable to open {0}\n'.format(texFile),file=sys.stderr)
			sys.stdout.flush()
			return None
			
		return texFile
		
	def __genPDF(self,texFile):
		'''
		generates a .pdf file based on a .tex file by calling the pdflatex compiler. errors will be logged in a log.txt.
		if successful the .pdf file name is returned, otherwise None is returned
		'''
		
		if os.path.isfile(texFile) == False:
			return None
		else:
			pdf = texFile[:-3] + 'pdf'
			
			try:
				check_call(['pdflatex',texFile,'>',pdf])
			except CalledProcessError as e:
				details = {'code':e.returncode,'output':e.output,'cmd':e.cmd}
				print('{0} caused a CalledProcessError (Error Code: {1}): {2}'.format(details['cmd'],details['code'],details['output']),file=sys.stderr)
				sys.stdout.flush()	
				return None
		
		return pdf
		
	def __clean(self):
		'''
		removes all the files the pdflatex compiler creates while generating a PDF from the given tex code.
		errors are written to log.txt
		'''
		
		try:
			os.remove(self.filename + '.log')
			os.remove(self.filename + '.aux')
			os.remove(self.filename + '.tex')
		except OSError as e:
			print('Unable to clean up LaTex files. {0} (Error Code: {1})\n'.format(e.strerror,e.errno),file=sys.stderr)
			sys.stdout.flush()
			
	def genAward(self):
		'''calls the preceeding "private" functions to generate and return a PDF award file'''
		
		texFile = self.__genTexFile(self.filename)
		
		if texFile is not None:
			pdf = self.__genPDF(texFile)
				
			if pdf is not None:
				self.__clean()
				return pdf
				
		return None