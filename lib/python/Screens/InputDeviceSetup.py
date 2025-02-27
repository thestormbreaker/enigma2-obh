from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Components.InputDevice import iInputDevices, iRcTypeControl
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.config import config, ConfigYesNo, getConfigListEntry, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import HelpableActionMap
from Components.SystemInfo import SystemInfo
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap


class InputDeviceSelection(Screen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Input Devices"))

		self.edittext = _("Press OK to edit the settings.")

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["introduction"] = StaticText(self.edittext)

		self.devices = [(iInputDevices.getDeviceName(x), x) for x in iInputDevices.getDeviceList()]
		print(("[InputDeviceSetup] found devices :->", len(self.devices), self.devices))

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
		{
		"cancel": (self.close, _("Exit input device selection.")),  # noqa: E122
		"ok": (self.okbuttonClick, _("Select input device.")),  # noqa: E122
		}, -2)

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
		{
		"red": (self.close, _("Exit input device selection.")),  # noqa: E122
		"green": (self.okbuttonClick, _("Select input device.")),  # noqa: E122
		}, -2)

		self.currentIndex = 0
		self.list = []
		self["list"] = List(self.list)
		self.updateList()
		self.onClose.append(self.cleanup)

	def cleanup(self):
		self.currentIndex = 0

	def buildInterfaceList(self, device, description, type, isinputdevice=True):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "div-h.png"))
		devicepng = None
		enabled = iInputDevices.getDeviceAttribute(device, 'enabled')
		# print("[InputDevice] device = %s, description = %s, type = %s, isinputdevice = %s, enabled = %s" % (device, description, type, isinputdevice, enabled))
		if type is None:
			devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcold-configured.png"))
		elif type == 'remote':
			if config.misc.rcused.value == 1:  # default is 1
				if enabled:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcold-configured.png"))
				else:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcold.png"))
			else:
				if enabled:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcnew-configured.png"))
				else:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcnew.png"))
		elif type == 'keyboard':
			if enabled:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_keyboard-configured.png"))
			else:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_keyboard.png"))
		elif type == 'mouse':
			if enabled:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_mouse-configured.png"))
			else:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_mouse.png"))
		elif isinputdevice:
			devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/input_rcnew.png"))
		return device, description, devicepng, divpng

	def updateList(self):
		self.list = []
		# print("[InputDevice] iRcTypeControl.multipleRcSupported = {}".format(iRcTypeControl.multipleRcSupported()))

		if iRcTypeControl.multipleRcSupported():
			self.list.append(self.buildInterfaceList('rctype', _('Select to configure remote control type'), None, False))

		for x in self.devices:
			dev_type = iInputDevices.getDeviceAttribute(x[1], 'type')
			self.list.append(self.buildInterfaceList(x[1], _(x[0]), dev_type))
		# print("[InputDevice] list = {}, self.currentIndex = {}".format(self.list, self.currentIndex))
		self["list"].setList(self.list)
		self["list"].setIndex(self.currentIndex)

	def okbuttonClick(self):
		selection = self["list"].getCurrent()
		self.currentIndex = self["list"].getIndex()
		# print "[InputDevice] selection = {}".format(selection)
		if selection is not None:
			# print("[InputDevice] selection[0] = {}".format(selection[0]))
			if selection[0] == 'rctype':
				self.session.open(RemoteControlType)
			else:
				self.session.openWithCallback(self.DeviceSetupClosed, InputDeviceSetup, selection[0])

	def DeviceSetupClosed(self, *ret):
		self.updateList()


class InputDeviceSetup(ConfigListScreen, Screen):
	def __init__(self, session, device=None):
		Screen.__init__(self, session)
		self.setTitle(_("Input Device Setup"))

		self.inputDevice = device
		iInputDevices.currentDevice = self.inputDevice
		self.enableEntry = None
		self.repeatEntry = None
		self.delayEntry = None
		self.nameEntry = None
		self.enableConfigEntry = None

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry, fullUI=True)

		self["introduction"] = StaticText()

		# for generating strings into .po only
		devicenames = [_("%s %s front panel") % (SystemInfo["MachineBrand"], SystemInfo["MachineName"]), _("%s %s remote control (native)") % (SystemInfo["MachineBrand"], SystemInfo["MachineName"]), _("%s %s advanced remote control (native)") % (SystemInfo["MachineBrand"], SystemInfo["MachineName"]), _("%s %s ir keyboard") % (SystemInfo["MachineBrand"], SystemInfo["MachineName"]), _("%s %s ir mouse") % (SystemInfo["MachineBrand"], SystemInfo["MachineName"])]  # noqa: F841

		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

	def layoutFinished(self):
		listWidth = self["config"].l.getItemSize().width()
		# use 20% of list width for sliders
		self["config"].l.setSeperation(int(listWidth * .8))

	def cleanup(self):
		iInputDevices.currentDevice = ""

	def createSetup(self):
		self.list = []
		self.enableEntry = getConfigListEntry(_("Change repeat and delay settings?"), getattr(config.inputDevices, self.inputDevice).enabled)
		self.repeatEntry = getConfigListEntry(_("Interval between keys when repeating:"), getattr(config.inputDevices, self.inputDevice).repeat)
		self.delayEntry = getConfigListEntry(_("Delay before key repeat starts:"), getattr(config.inputDevices, self.inputDevice).delay)
		self.nameEntry = getConfigListEntry(_("Devicename:"), getattr(config.inputDevices, self.inputDevice).name)
		if self.enableEntry:
			if isinstance(self.enableEntry[1], ConfigYesNo):
				self.enableConfigEntry = self.enableEntry[1]

		self.list.append(self.enableEntry)
		if self.enableConfigEntry:
			if self.enableConfigEntry.value is True:
				self.list.append(self.repeatEntry)
				self.list.append(self.delayEntry)
			else:
				self.repeatEntry[1].setValue(self.repeatEntry[1].default)
				self["config"].invalidate(self.repeatEntry)
				self.delayEntry[1].setValue(self.delayEntry[1].default)
				self["config"].invalidate(self.delayEntry)
				self.nameEntry[1].setValue(self.nameEntry[1].default)
				self["config"].invalidate(self.nameEntry)

		self["config"].list = self.list
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		if self["config"].getCurrent() == self.enableEntry:
			self["introduction"].setText(_("Current device: ") + str(iInputDevices.getDeviceAttribute(self.inputDevice, 'name')))
		else:
			self["introduction"].setText(_("Current value: ") + self.getCurrentValue() + ' ' + _("ms"))

	def newConfig(self):
		current = self["config"].getCurrent()
		if current:
			if current == self.enableEntry:
				self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def keySelect(self):
		ConfigListScreen.keySelect(self)
		self.newConfig()

	def confirm(self, confirmed):
		if not confirmed:
			print("[InputDeviceSetup] not confirmed")
			return
		else:
			self.nameEntry[1].setValue(iInputDevices.getDeviceAttribute(self.inputDevice, 'name'))
			getattr(config.inputDevices, self.inputDevice).name.save()
			self.keySave()

	def apply(self):
		self.session.openWithCallback(self.confirm, MessageBox, _("Use these input device settings?"), MessageBox.TYPE_YESNO, timeout=20, default=True)

	# for summary:
	def changedEntry(self):
		ConfigListScreen.changedEntry(self)
		self.selectionChanged()  # to update hints text from the slider in real time.

	def getCurrentValue(self):  # required because getCurrentValue() in ConfigListScreen outputs .getText() e.g. '100/500' rather than just .value, '100' and this is what is wanted in the hints text.
		return str(self["config"].getCurrent()[1].value)


class RemoteControlType(ConfigListScreen, Screen):
	odinRemote = "OdinM9"
	if SystemInfo["boxtype"] == "maram9":
		odinRemote = "MaraM9"

	rcList = [
		("0", _("Default")),
		("3", _(odinRemote)),
		("4", _("DMM normal")),
		("5", _("et9000/et9100")),
		("6", _("DMM advanced")),
		("7", _("et5000/6000")),
		("8", _("VU+")),
		("9", _("et8000/et10000")),
		("11", _("et9200/9500/6500")),
		("13", _("et4000")),
		("14", _("XP1000")),
		("16", _("HD11/HD51/HD1100/HD1200/HD1265/HD1500/HD500C/HD530C/et7x00/et8500")),
		("17", _("XP3000")),
		("18", _("F1/F3/F4/F4-TURBO/TRIPLEX")),
		("19", _("HD2400")),
		("20", _("Zgemma Star S/2S/H1/H2")),
		("21", _("Zgemma H.S/H.2S/H.2H/H5")),
		("22", _("Zgemma i55")),
		("23", _("WWIO 4K")),
		("24", _("Axas E4HD Ultra")),
		("25", _("Zgemma H9/I55Plus old Model")),
		("26", _("Protek 4K UHD/HD61")),
		("27", _("HD60/Multiboxpro")),
		("28", _("H7/H9/H9COMBO/H10 new Model")),
		("30", _("PULSe 4K/4K Mini"))
	]

	defaultRcList = [
		("default", 0),
		("et4000", 13),
		("et5000", 7),
		("et6000", 7),
		("et6500", 11),
		("et7x00", 16),
		("et8000", 9),
		("et8500", 16),
		("et9000", 5),
		("et9100", 5),
		("et9200", 11),
		("et9500", 11),
		("et10000", 9),
		("formuler1", 18),
		("formuler3", 18),
		("hd11", 16),
		("hd51", 16),
		("hd52", 16),
		("hd1100", 16),
		("hd1200", 16),
		("hd1265", 16),
		("hd500c", 16),
		("hd530c", 16),
		("hd2400", 19),
		("h3", 21),
		("h5", 21),
		# ("h7", 21),# old model
		("i55", 22),
		("bre2ze4k", 23),
		("e4hd", 24),
		# ("h9", 25),# old model
		("i55plus", 25),
		("protek4k", 26),
		("hd61", 26),
		("hd60", 27),
		("multiboxpro", 27),
		("h7", 28),  # new model
		("h9", 28),  # new model
		("h9combo", 28),
		("h10", 28),
		("h11", 28),
		("pulse4k", 30),
		("pulse4kmini", 30)
	]

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["RemoteControlType", "Setup"]

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, fullUI=True)

		rctype = config.plugins.remotecontroltype.rctype.value
		self.rctype = ConfigSelection(choices=self.rcList, default=str(rctype))
		self.list.append(getConfigListEntry(_("Remote control type"), self.rctype))
		self["config"].list = self.list

		self.defaultRcType = 0
		self.getDefaultRcType()

	def getDefaultRcType(self):
		boxtype = SystemInfo["model"]
		procBoxtype = iRcTypeControl.getBoxType()
		print("[InputDevice] procBoxtype = %s, self.boxType = %s" % (procBoxtype, boxtype))
		for x in self.defaultRcList:
			if x[0] in boxtype or x[0] in procBoxtype:
				self.defaultRcType = x[1]
				break
		# If there is none in the list, use the current value...
		#
		# print("[InputDevice] self.defaultRcType 1 = {}".format(self.defaultRcType))
		if self.defaultRcType == 0:
			self.defaultRcType = iRcTypeControl.readRcType()
		# print("[InputDevice] self.defaultRcType 2 = {}".format(self.defaultRcType))

	def setDefaultRcType(self):
		iRcTypeControl.writeRcType(self.defaultRcType)

	def keySave(self):
		if config.plugins.remotecontroltype.rctype.value == int(self.rctype.value):
			self.close()
		else:
			self.setNewSetting()
			self.session.openWithCallback(self.keySaveCallback, MessageBox, _("Is this setting ok?"), MessageBox.TYPE_YESNO, timeout=20, default=True, timeout_default=False)

	def keySaveCallback(self, answer):
		if answer is False:
			self.restoreOldSetting()
		else:
			config.plugins.remotecontroltype.rctype.value = int(self.rctype.value)
			config.plugins.remotecontroltype.save()
			self.close()

	def restoreOldSetting(self):
		if config.plugins.remotecontroltype.rctype.value == 0:
			self.setDefaultRcType()
		else:
			iRcTypeControl.writeRcType(config.plugins.remotecontroltype.rctype.value)

	def setNewSetting(self):
		if int(self.rctype.value) == 0:
			self.setDefaultRcType()
		else:
			iRcTypeControl.writeRcType(int(self.rctype.value))

	def keyCancel(self):
		self.restoreOldSetting()
		self.close()
