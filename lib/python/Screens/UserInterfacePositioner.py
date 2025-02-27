from os import access, R_OK
import traceback
from enigma import getDesktop

from Components.ActionMap import ActionMap
from Components.config import config, configfile, getConfigListEntry, ConfigSelectionNumber, NoSave, ConfigNumber
from Components.ConfigList import ConfigListScreen
from Components.Console import Console
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Tools.Directories import fileExists


def getFilePath(setting):
	return "/proc/stb/fb/dst_%s" % (setting)



def setPositionParameter(parameter, configElement):
	f = open(getFilePath(parameter), "w")
	f.write('%08X\n' % configElement.value)
	f.close()
	if fileExists(getFilePath("apply")):
		f = open(getFilePath("apply"), "w")
		f.write('1')
		f.close()
	# This is a horrible hack to work around a problem with Vu+ not updating the background properly
	# when changing height. Previously the background only updated after changing the width fields.
	elif parameter != "width" and fileExists(getFilePath("width")):
		f = open(getFilePath("width"), "w")
		f.write('%08X\n' % config.osd.dst_width.value)
		f.close()


def InitOsd():
	config.osd.dst_left = ConfigSelectionNumber(default=0, stepwidth=1, min=0, max=720, wraparound=False)
	config.osd.dst_width = ConfigSelectionNumber(default=720, stepwidth=1, min=0, max=720, wraparound=False)
	config.osd.dst_top = ConfigSelectionNumber(default=0, stepwidth=1, min=0, max=576, wraparound=False)
	config.osd.dst_height = ConfigSelectionNumber(default=576, stepwidth=1, min=0, max=576, wraparound=False)
	config.osd.alpha = ConfigSelectionNumber(default=255, stepwidth=1, min=0, max=255, wraparound=False)
	config.misc.osd_alpha = NoSave(ConfigNumber(default=255))

def InitOsdPosition():
	SystemInfo["CanChangeOsdAlpha"] = access('/proc/stb/video/alpha', R_OK) and True or False
	SystemInfo["CanChangeOsdPosition"] = access('/proc/stb/fb/dst_left', R_OK) and True or False
	SystemInfo["OsdSetup"] = SystemInfo["CanChangeOsdPosition"]

	if SystemInfo["CanChangeOsdAlpha"] is True or SystemInfo["CanChangeOsdPosition"] is True:
		SystemInfo["OsdMenu"] = True
	else:
		SystemInfo["OsdMenu"] = False

	def setOSDLeft(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			setPositionParameter("left", configElement)
	config.osd.dst_left.addNotifier(setOSDLeft)

	def setOSDWidth(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			setPositionParameter("width", configElement)
	config.osd.dst_width.addNotifier(setOSDWidth)

	def setOSDTop(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			setPositionParameter("top", configElement)
	config.osd.dst_top.addNotifier(setOSDTop)

	def setOSDHeight(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			setPositionParameter("height", configElement)
	config.osd.dst_height.addNotifier(setOSDHeight)
	print('[UserInterfacePositioner] Setting OSD position: %s %s %s %s' % (config.osd.dst_left.value, config.osd.dst_width.value, config.osd.dst_top.value, config.osd.dst_height.value))

	def setOSDAlpha(configElement):
		if SystemInfo["CanChangeOsdAlpha"]:
			print('[UserInterfacePositioner] Setting OSD alpha:', str(configElement.value))
			config.misc.osd_alpha.setValue(configElement.value)
			f = open("/proc/stb/video/alpha", "w")
			f.write(str(configElement.value))
			f.close()
	config.osd.alpha.addNotifier(setOSDAlpha)


class UserInterfacePositioner(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("OSD position"))
		self.ConsoleB = Console(binary=True)
		self["status"] = StaticText()
		self["key_yellow"] = StaticText(_("Defaults"))

		self["actions"] = ActionMap(["ColorActions"],
			{
				"yellow": self.keyDefault,
			}, -2)  # noqa: E123
		self.alpha = config.osd.alpha.value
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry, fullUI=True)
		if SystemInfo["CanChangeOsdAlpha"]:
			self.list.append(getConfigListEntry(_("User interface visibility"), config.osd.alpha, _("This option lets you adjust the transparency of the user interface")))
		if SystemInfo["CanChangeOsdPosition"]:
			self.list.append(getConfigListEntry(_("Move Left/Right"), config.osd.dst_left, _("Use the LEFT/RIGHT buttons on your remote to move the user interface left/right.")))
			self.list.append(getConfigListEntry(_("Width"), config.osd.dst_width, _("Use the LEFT/RIGHT buttons on your remote to adjust the width of the user interface. LEFT button decreases the size, RIGHT increases the size.")))
			self.list.append(getConfigListEntry(_("Move Up/Down"), config.osd.dst_top, _("Use the LEFT/RIGHT buttons on your remote to move the user interface up/down.")))
			self.list.append(getConfigListEntry(_("Height"), config.osd.dst_height, _("Use the LEFT/RIGHT buttons on your remote to adjust the height of the user interface. LEFT button decreases the size, RIGHT increases the size.")))
		self["config"].list = self.list

		self.serviceRef = None
		if "wizard" not in str(traceback.extract_stack()).lower():
			self.onClose.append(self.__onClose)
		if self.welcomeWarning not in self.onShow:
			self.onShow.append(self.welcomeWarning)
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self["status"].setText(self["config"].getCurrent()[2])

	def welcomeWarning(self):
		if self.welcomeWarning in self.onShow:
			self.onShow.remove(self.welcomeWarning)
		popup = self.session.openWithCallback(self.welcomeAction, MessageBox, _("NOTE: This feature is intended for people who cannot disable overscan "
			"on their television / display.  Please first try to disable overscan before using this feature.\n\n"
			"USAGE: Adjust the screen size and position settings so that the shaded user interface layer *just* "
			"covers the test pattern in the background.\n\n"
			"Select Yes to continue or No to exit."), type=MessageBox.TYPE_YESNO, timeout=-1, default=False)
		popup.setTitle(_("OSD position"))

	def welcomeAction(self, answer):
		if answer:
			self.serviceRef = self.session.nav.getCurrentlyPlayingServiceReference()
			self.session.nav.stopService()
			if self.restoreService not in self.onClose:
				self.onClose.append(self.restoreService)
			self.ConsoleB.ePopen('/usr/bin/showiframe /usr/share/enigma2/hd-testcard.mvi')
			# config.osd.alpha.setValue(155)
		else:
			self.close()

	def restoreService(self):
		try:
			self.session.nav.playService(self.serviceRef)
		except:
			pass

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewPosition()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewPosition()

	def keyDefault(self):
		config.osd.alpha.setValue(255)
		config.osd.dst_left.setValue(0)
		config.osd.dst_width.setValue(720)
		config.osd.dst_top.setValue(0)
		config.osd.dst_height.setValue(576)
		for item in self["config"].list:
			self["config"].invalidate(item)
		print('[UserInterfacePositioner] Setting default OSD position: %s %s %s %s' % (config.osd.dst_left.value, config.osd.dst_width.value, config.osd.dst_top.value, config.osd.dst_height.value))

	def setPreviewPosition(self):
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()
		dsk_w = int(float(size_w)) / float(720)
		dsk_h = int(float(size_h)) / float(576)
		dst_left = int(config.osd.dst_left.value)
		dst_width = int(config.osd.dst_width.value)
		dst_top = int(config.osd.dst_top.value)
		dst_height = int(config.osd.dst_height.value)
		while dst_width + (dst_left / float(dsk_w)) >= 720.5 or dst_width + dst_left > 720:
			dst_width = int(dst_width) - 1
		while dst_height + (dst_top / float(dsk_h)) >= 576.5 or dst_height + dst_top > 576:
			dst_height = int(dst_height) - 1
		config.osd.dst_left.setValue(dst_left)
		config.osd.dst_width.setValue(dst_width)
		config.osd.dst_top.setValue(dst_top)
		config.osd.dst_height.setValue(dst_height)
		for item in self["config"].list:
			self["config"].invalidate(item)
		print('[UserInterfacePositioner] Setting OSD position: %s %s %s %s' % (config.osd.dst_left.value, config.osd.dst_width.value, config.osd.dst_top.value, config.osd.dst_height.value))

	def __onClose(self):
		self.ConsoleB.ePopen('/usr/bin/showiframe /usr/share/backdrop.mvi')

	# This is called by the Wizard...

	def run(self):
		# config.osd.alpha.setValue(self.alpha)
		config.osd.dst_left.save()
		config.osd.dst_width.save()
		config.osd.dst_top.save()
		config.osd.dst_height.save()
		configfile.save()
		self.close()
