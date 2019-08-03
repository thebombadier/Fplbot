import praw, datetime, logging, urllib.request, pandas as pd, json, smtplib, sys, os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


COMMASPACE = ', '

logging.basicConfig(filename='whole.log',level=logging.WARNING)



def NonAscii(word, NonAsciiTrans):
	converted_word = ''
	for char in word:
		transchar = ''
		if char in NonAsciiTrans:
			transchar = NonAsciiTrans[char]
		else:
			transchar = char
		converted_word += transchar
	return converted_word

def checktype(DreamTeam, Type):
	if Type == "Defend" or Type == "Midfield":
		x = 5
	if Type == "Forward":
		x = 3
	if Type == "Goalkeeper":
		x = 2
	if len(DreamTeam[DreamTeam['Type'] == Type]) < x:
		return True
	else:
		return False

def adddata(DreamTeam):
	NonAsciiTrans={
	"ü" : "u",
	"é" : "e",
	"ó" : "o",
	"ñ" : "n",
	"í" : "i",
	"á" : "a",
	"ß" : "a",
	"ö" : "o",
	"Ö" : "o",
	"ä" : "a"
	}
	with urllib.request.urlopen("https://fantasy.premierleague.com/api/bootstrap-static/") as url:
		data = json.loads(url.read().decode())
	for i in range (0,len(DreamTeam['Name'])):
		Name = str(DreamTeam.loc[i,"Name"])
		position = str(DreamTeam.loc[i,"Type"])
		Team = str(DreamTeam.loc[i,"Team"])
		for player in data["elements"]:
			firstname = NonAscii(player["first_name"],NonAsciiTrans)
			secondname = NonAscii(player["second_name"],NonAsciiTrans)
			teamno = player["team"]-1
			teamname = data["teams"][teamno]["name"]
			if (Name == firstname and Team == teamname) or (Name == secondname and Team == teamname):
				value = player["now_cost"]
				DreamTeam.loc[i,"value"] = value
	return DreamTeam
def convertdate(date):
	date = datetime.datetime.strptime(date, '%Y-%m-%d')
	date = date.date()
	return date
def sendmail(text):
	sender = ''
	gmail_password = ''
	recipients = ['']
	
	# Create the enclosing (outer) message
	outer = MIMEMultipart()
	outer['Subject'] = 'New Team Ready'
	outer['To'] = COMMASPACE.join(recipients)
	outer['From'] = sender
	outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'
	outer.attach(MIMEText(text, 'plain')) # or 'html'
	# List of attachments
	attachments = ['team.csv']

	# Add the attachments to the message
	for file in attachments:
		try:
			with open(file, 'rb') as fp:
				msg = MIMEBase('application', "octet-stream")
				msg.set_payload(fp.read())
			encoders.encode_base64(msg)
			msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file))
			outer.attach(msg)
		except:
			print("Unable to open one of the attachments. Error: ", sys.exc_info()[0])
			raise

	composed = outer.as_string()

	# Send the email
	try:
		with smtplib.SMTP('smtp.gmail.com', 587) as s:
			s.ehlo()
			s.starttls()
			s.ehlo()
			s.login(sender, gmail_password)
			s.sendmail(sender, recipients, composed)
			s.close()
		print("Email sent!")
	except:
		print("Unable to send the email. Error: ", sys.exc_info()[0])
		raise

def DreamTeam():
	print("Loading Old Team...")
	DreamTeam = pd.read_csv('DreamTeam.csv')
	RealTeam = pd.DataFrame(columns=DreamTeam.columns)
	TotalValue = 0
	TotalMention = 0
	DreamTeam = adddata(DreamTeam)
	print ("Creating Team ...")
	for i in range (0,len(DreamTeam['Name'])):
		Team = str(DreamTeam.loc[i,"Team"])
		Type = str(DreamTeam.loc[i, "Type"])
		value = int(DreamTeam.loc[i, "value"])
		count = int(DreamTeam.loc[i, "Count"])
		Name = str(DreamTeam.loc[i,"Name"])
		if TotalValue + value < 1000 and len(RealTeam[RealTeam['Team'] == Team]) < 2 and checktype(RealTeam, Type):
			x = DreamTeam.loc[DreamTeam['Name'] == Name]
			RealTeam = RealTeam.append(x, ignore_index=True)
			TotalValue = TotalValue + value
			TotalMention = TotalMention + count
	x = RealTeam.sort_values(['Type','value'], ascending=[True, False])
	y = "Total Price: £" + str(TotalValue/10)
	a = "Total Mentions: " + str(TotalMention)
	text = y + "\n" + a
	#password = 'gpzygzoglccqpuvu' # Your email account password
	#send_to_email = 'tomandthenews@gmail.com' # Who you are sending the message to
	#email1 = y + z
	y = x.to_html('df.html')
	x.to_csv('team.csv', index=False)
	sendmail(text)
	print(x)
	print(y)
	print(a)
def schedule(var):
	now = datetime.datetime.today().date()
	done = False
	schedule = pd.read_csv('schedule.csv')
	for x in range(0,len(schedule['Gameweek'])):
		GW = str(schedule.loc[x,"Gameweek"])
		date = convertdate(str(schedule.loc[x,"Date"]))
		transferday = convertdate(str(schedule.loc[x,"TransferDay"]))
		nextdate = convertdate(str(schedule.loc[x,"Deadline"]))
		if now == transferday:
			if var == "type":
				return 2
		if x < 38:
			if now > date and now < nextdate:
				if var == "type":
					res = 0
				if var == "GW":
					res = GW
		# its the start of a new GameWeek !
		if now == date:
			if var == "type":
				res = 1
			if var == "GW":
				res = GW
		if now == nextdate:
			if var == "type":
				res = 3
			if var == "GW":
				res = GW
		# regardless time to update DreamTeam
		# active teamcode if its transfer day
	return res

def main():
	print("Loading bot ...")
	reddit = praw.Reddit(client_id="", client_secret="", user_agent="")
	print("Loading Comments...")
	submission = reddit.subreddit('FantasyPL').sticky(number=1)
	forbidchar = ["(",")",",","[","]"]
	MasterVote = pd.read_csv('fpl.csv')
	submission.comments.replace_more(limit=None)
	print("Comments loaded")
	print("Parsing Comments...")
	sked = schedule("type")

	for i in  range(0,len(MasterVote['Name'])):
		count = 0
		Name = str(MasterVote.loc[i,"Name"])
		OName = str(MasterVote.loc[i,"Other"])
		Team = str(MasterVote.loc[i,"Team"])
		ci = 0
		rc = 0

		for top_level_comment in submission.comments:
			nums = Name.split()
			ci = ci + 1
			for char in forbidchar:
				bodytext = top_level_comment.body.strip(char)
			if len(nums) == 1:
				words = bodytext.split()
				for word in words:
					if word == Name or OName == word:
						rc = rc + 1
			words = bodytext.splitlines()
			for word in words:
				if Name in word or OName in word:
					count = count + 1
		if len(nums) == 1 and rc * 10 < count:
			count = 0
		if Name == "King" and Team == "Leicester":
			count = 0
		if Name == "Jota" and Team == "Aston Villa":
			count = 0
		if Name == "Kelly" and Team == "Bournemouth":
			count = 0
		GW = schedule("GW")
		# update CSVs
		if sked == 0 or sked == 2:
			total = MasterVote.loc[i,GW]
			total = total + count
			MasterVote.loc[i,"Count"] = count
			MasterVote.loc[i,GW] = total
		if sked == 1:
			MasterVote.loc[i,"Count"] = count
			MasterVote.loc[i,GW] = count
		if sked == 3:
			continue
	#If Transfey day run code
	x = "comments parsed"
	if sked == 1:
		a = "Its a new Gameweek:"
		print(a, GW)
	if sked == 0:
		a = "Updating Count for"
		print(a, GW)
	if sked == 3:
		a = "Its Deadline day for"
		print(a, GW)
	print(ci, x)
	print("Uploading to csv...")
	MasterVote.to_csv('fpl.csv', index=False)
	x = MasterVote.sort_values(by='Count', ascending=False)
	z = x.head(30)
	z.to_csv('dreamteam.csv', index=False)
	print("Uploaded to csv!")
	if sked == 2:
		print("Its Transfer Day, creating team...")
		DreamTeam()

		#MasterVote.loc[i,"Count"] = count
		#MasterVote.loc[i,x] = count

if __name__== "__main__":
  main()










