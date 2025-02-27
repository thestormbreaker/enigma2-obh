from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo, OEA
from Screens.Screen import Screen, ScreenSummary

from enigma import eTimer
from sys import modules
from datetime import datetime
from json import loads
# required methods: Request, urlopen, HTTPError, URLError
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

if SystemInfo["imagetype"] != 'developer':
	ImageVer = "%03d" % int(SystemInfo["imagebuild"])
else:
	ImageVer = "%s.%s" % (SystemInfo["imagebuild"], SystemInfo["imagedevbuild"])
	ImageVer = float(ImageVer)

E2Branches = {
    'developer': 'Python3.12',
    'release': 'Python3.12',
    'community': 'Python3.12'
}
CommitLogs = [
	(f"https://api.github.com/repos/oe-alliance/oe-alliance-core/commits?sha={OEA}", "OE-A Core"),
	("https://api.github.com/repos/BlackHole/enigma2/commits?sha=%s" % getattr(E2Branches, SystemInfo["imagetype"], "Python3.12"), "Enigma2"),
	("https://api.github.com/repos/BlackHole/skins/commits", "OpenBh Skins"),
	("https://api.github.com/repos/oe-alliance/oe-alliance-plugins/commits", "OE-A Plugins"),
	("https://api.github.com/repos/oe-alliance/AutoBouquetsMaker/commits", "AutoBouquetsMaker"),
	("https://api.github.com/repos/oe-alliance/branding-module/commits", "Branding Module"),
]
project = 0
cachedProjects = {}


def readGithubCommitLogsSoftwareUpdate():
	global ImageVer
	gitstart = True
	url = CommitLogs[project][0]
	commitlog = ""
	try:
		try:
			from ssl import _create_unverified_context
			req = Request(url)
			log = loads(urlopen(req, timeout=5, context=_create_unverified_context()).read())
		except:
			log = loads(urlopen(req, timeout=5).read())
		for c in log:
			if c['commit']['message'].startswith('openvix:') or (gitstart and not c['commit']['message'].startswith('openbh:') and getScreenTitle() in ("OE-A Core", "Enigma2", "OpenBh Skins")):
					continue
			if c['commit']['message'].startswith('openbh:'):
				gitstart = False
				if SystemInfo["imagetype"] != 'developer' and c['commit']['message'].startswith('openbh: developer'):
					print('[GitCommitLog] Skipping developer line')
					continue
				elif SystemInfo["imagetype"]  == 'developer' and c['commit']['message'].startswith('openbh: release') or c['commit']['message'].startswith('openbh: community'):
					print('[GitCommitLog] Skipping release/community line')
					continue
				tmp = c['commit']['message'].split(' ')[2].split('.')
				if len(tmp) > 2:
					if SystemInfo["imagetype"] != 'developer':
						releasever = tmp[2]
						releasever = "%03d" % int(releasever)
					else:
						releasever = '%s.%s' % (tmp[2], tmp[3])
						releasever = float(releasever)
				if ImageVer >= releasever:
					break

			creator = c['commit']['author']['name']
			title = c['commit']['message']
			date = datetime.strptime(c['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ').strftime('%x %X')
			commitlog += date + ' ' + creator + '\n' + title + 2 * '\n'
		cachedProjects[getScreenTitle()] = commitlog
	except HTTPError as err:
		if err.code == 403:
			print('[GitCommitLog] It seems you have hit your API limit - please try again later.', err)
			commitlog += _("It seems you have hit your API limit - please try again later.")
		else:
			print('[GitCommitLog] The commit log cannot be retrieved at the moment - please try again later.', err)
			commitlog += _("The commit log cannot be retrieved at the moment - please try again later.")
	except URLError as err:
		print('[GitCommitLog] The commit log cannot be retrieved at the moment - please try again later.', err)
		commitlog += _("The commit log cannot be retrieved at the moment - please try again later.\n")
	except Exception as err:
		print('[GitCommitLog] The commit log cannot be retrieved at the moment - please try again later.', err)
		commitlog += _("The commit log cannot be retrieved at the moment - please try again later.")
	return commitlog


def readGithubCommitLogs():
	global ImageVer
	global cachedProjects
	cachedProjects = {}
	blockstart = False
	gitstart = True
	url = CommitLogs[project][0]
	commitlog = ""
	try:
		try:
			from ssl import _create_unverified_context
			req = Request(url)
			log = loads(urlopen(req, timeout=5, context=_create_unverified_context()).read())
		except:
			log = loads(urlopen(req, timeout=5).read())
		for c in log:
			if c['commit']['message'].startswith('openvix:') or (gitstart and not c['commit']['message'].startswith('openbh:') and getScreenTitle() in ("OE-A Core", "Enigma2", "OpenBh Skins")):
				continue
			if c['commit']['message'].startswith('openbh:'):
				blockstart = False
				gitstart = False
				if SystemInfo["imagetype"] != 'developer' and c['commit']['message'].startswith('openbh: developer'):
					print('[GitCommitLog] Skipping developer line')
					continue
				elif SystemInfo["imagetype"] == 'developer' and c['commit']['message'].startswith('openbh: release') or c['commit']['message'].startswith('openbh: community'):
					print('[GitCommitLog] Skipping release/community line')
					continue
				tmp = c['commit']['message'].split(' ')[2].split('.')
				if len(tmp) > 2:
					if SystemInfo["imagetype"] != 'developer':
						releasever = tmp[2]
						releasever = "%03d" % int(releasever)
					else:
						releasever = '%s.%s' % (tmp[2], tmp[3])
						releasever = float(releasever)
				if releasever > ImageVer:
					blockstart = True
					continue
			elif blockstart and getScreenTitle() in ("OE-A Core", "Enigma2", "OpenBh Skins"):
				blockstart = True
				continue

			creator = c['commit']['author']['name']
			title = c['commit']['message']
			date = datetime.strptime(c['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ').strftime('%x %X')
			commitlog += date + ' ' + creator + '\n' + title + 2 * '\n'
		cachedProjects[getScreenTitle()] = commitlog
	except HTTPError as err:
		if err.code == 403:
			print('[GitCommitLog] It seems you have hit your API limit - please try again later.', err)
			commitlog += _("It seems you have hit your API limit - please try again later.")
		else:
			print('[GitCommitLog] The commit log cannot be retrieved at the moment - please try again later.', err)
			commitlog += _("The commit log cannot be retrieved at the moment - please try again later.")
	except URLError as err:
		print('[GitCommitLog] The commit log cannot be retrieved at the moment - please try again later.', err)
		commitlog += _("The commit log cannot be retrieved at the moment - please try again later.\n")
	except Exception as err:
		print('[GitCommitLog] The commit log cannot be retrieved at the moment - please try again later.', err)
		commitlog += _("The commit log cannot be retrieved at the moment - please try again later.")
	return commitlog


def getScreenTitle():
	return CommitLogs[project][1]


def left():
	global project
	project = project == 0 and len(CommitLogs) - 1 or project - 1


def right():
	global project
	project = project != len(CommitLogs) - 1 and project + 1 or 0


gitcommitinfo = modules[__name__]


class CommitInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["CommitInfo", "AboutOE"]
		self["AboutScrollLabel"] = ScrollLabel(_("Please wait"))
		self["HintText"] = Label(_("Press up/down to scroll through the selected log\n\nPress left/right to see different log types"))

		self["actions"] = ActionMap(["SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown,
				"left": self.left,
				"right": self.right
			}  # noqa: E123
		)

		self["key_red"] = Button(_("Cancel"))
		self.onUpdate = []

		self.Timer = eTimer()
		self.Timer.callback.append(self.readGithubCommitLogs)
		self.Timer.start(50, True)

	def readGithubCommitLogs(self):
		self.setTitle(gitcommitinfo.getScreenTitle())
		self["AboutScrollLabel"].setText(gitcommitinfo.readGithubCommitLogs())
		self.update()

	def updateCommitLogs(self):
		if gitcommitinfo.getScreenTitle() in gitcommitinfo.cachedProjects:
			self.setTitle(gitcommitinfo.getScreenTitle())
			self["AboutScrollLabel"].setText(gitcommitinfo.cachedProjects[gitcommitinfo.getScreenTitle()])
			self.update()
		else:
			self["AboutScrollLabel"].setText(_("Please wait"))
			self.Timer.start(50, True)

	def update(self):
		for x in self.onUpdate:
			x()

	def left(self):
		gitcommitinfo.left()
		self.updateCommitLogs()

	def right(self):
		gitcommitinfo.right()
		self.updateCommitLogs()

	def closeRecursive(self):
		self.close(("menu", "menu"))

	def createSummary(self):
		return CommitInfoSummary


class CommitInfoSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self.commitText = []
		self["commitText"] = StaticText()
		self.timer = eTimer()
		self.timer.callback.append(self.update)
		if self.changed not in parent.onUpdate:
			parent.onUpdate.append(self.changed)
		self.changed()

	def update(self):
		self.timer.stop()
		if self.commitText:
			self.commitText.append(self.commitText.pop(0))
			self["commitText"].text = "\n\n".join(self.commitText)
			self.timer.start(2000, 1)

	def changed(self):
		self.timer.stop()
		self["Title"].text = self.parent.getTitle()
		if self.parent["AboutScrollLabel"].getText():
			self.commitText = self.parent["AboutScrollLabel"].getText().split("\n\n")
			self["commitText"].text = "\n\n".join(self.commitText)
			self.timer.start(3000, 1)
