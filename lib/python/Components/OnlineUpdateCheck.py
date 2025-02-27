from time import time

from enigma import eTimer
from Components.About import about
from Components.config import config
from Components.Ipkg import IpkgComponent
from Components.SystemInfo import SystemInfo
import Components.Task

import socket
import sys
from urllib.request import urlopen, Request

error = 0


def OnlineUpdateCheck(session=None, **kwargs):
	global onlineupdatecheckpoller

	# The onlineupdatecheckpoller will be created (see below) after
	# OnlineUpdateCheckPoller is set-up, which is will be before we can ever
	# run.
	onlineupdatecheckpoller.start()


class FeedsStatusCheck:
	def __init__(self):
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

	def IsInt(self, val):
		try:
			int(val)
			return True
		except ValueError:
			return False

	def adapterAvailable(self):  # Box has an adapter configured and active
		for adapter in ("eth0", "eth1", "wlan0", "wlan1", "wlan2", "wlan3", "ra0"):
			if "addr" in about.getIfConfig(adapter):
				print("[OnlineUpdateCheck][adapterAvailable] PASSED")
				return True
		print("[OnlineUpdateCheck][adapterAvailable] FAILED")
		return False

	def NetworkUp(self, host="8.8.8.8", port=53, timeout=2):  # Box can access outside the local network
		return True  # bypass this function

		# Avoids DNS resolution
		# Avoids application layer (HTTP/FTP/IMAP)
		# Avoids calls to external utilities
		# Used "sudo nmap 8.8.8.8" to discover the following
		# Host: 8.8.8.8 (google-public-dns-a.google.com)
		# OpenPort: 53/tcp
		# Service: domain (DNS/TCP)
		previousTimeout = socket.getdefaulttimeout()
		socket.setdefaulttimeout(timeout)
		try:
			sd = None
			sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
			sd.connect((host, port))
			print("[OnlineUpdateCheck][NetworkUp] PASSED")
			result = True
		except Exception as err:
			print("[OnlineUpdateCheck][NetworkUp] FAILED", err)
			result = False
		finally:
			if sd is not None:
				try:
					sd.shutdown(socket.SHUT_RDWR)
				except:
					pass
				sd.close()
		socket.setdefaulttimeout(previousTimeout)  # Reset to previous value.
		return result

	def getFeedStatus(self):
		officialReleaseFeedsUri = "openbh.net"
		status = 1
		trafficLight = "unknown"
		if self.adapterAvailable():
			if self.NetworkUp():
				if SystemInfo["imagetype"] == "release" and officialReleaseFeedsUri in SystemInfo["feedsurl"]:  # we know the network is good now so only do this check on release images where the release domain applies
					try:
						print("[OnlineUpdateCheck][getFeedStatus] checking feeds state")
						#req = Request("http://openvix.co.uk/TrafficLightState.php")
						#d = urlopen(req, timeout=3)
						#trafficLight = d.read().decode()
						if trafficLight == "stable":
							status = 0
						print("trafficLight", trafficLight)
					except Exception as err:
						print("[OnlineUpdateCheck][getFeedStatus] ERROR:", err)
						if hasattr(err, "code"):
							trafficLight = err.code
						else:
							trafficLight = type(err).__name__
				elif SystemInfo["imagetype"] == "developer" and "openbhdev" in SystemInfo["feedsurl"]:
					print("[OnlineUpdateCheck][getFeedStatus] Official developer feeds")
					trafficLight = "developer"
				else:  # if not using official feeds mark as alien. There is no status test for alien feeds (including official developer feeds).
					print("[OnlineUpdateCheck][getFeedStatus] Alien feeds url: %s" % SystemInfo["feedsurl"])
					status = 0
					trafficLight = "alien"
				config.softwareupdate.updateisunstable.value = status
				return trafficLight
			else:  # network not up
				print("[OnlineUpdateCheck][getFeedStatus] ERROR: -2")
				return -2
		else:  # adapter not available
			print("[OnlineUpdateCheck][getFeedStatus] ERROR: -3")
			return -3

	# We need a textual mapping for all possible return states for use by
	# SoftwareUpdate::checkNetworkState() and ChoiceBox::onshow()
	# Declared here for consistency and co-location with choices.

	feed_status_msgs = {
		"stable": _("Feeds status: Stable"),
		"unstable": _("Feeds status: Unstable"),
		"updating": _("Feeds status: Updating"),
		"-2": _("ERROR: No internet found"),
		"-3": _("ERROR: No network found"),
		"403": _("ERROR: Response 403 Forbidden"),
		"404": _("ERROR: Response 404 Not Found"),
		"inprogress": _("ERROR: Check is already running in background, please wait a few minutes and try again"),
		"unknown": _("Feeds status: Unknown"),
		"alien": _("Feeds status: Unknown, user feeds url"),
		"developer": _("Feeds status: Official developer feeds"),
	}

	def getFeedsBool(self):
		global error
		self.feedstatus = self.getFeedStatus()
		if self.feedstatus in (-2, -3, 403, 404):
			print("[OnlineUpdateCheck][getFeedsBool] Error %s" % str(self.feedstatus))
			return str(self.feedstatus)  # must be str as used in string keys of feed_status_msgs
		elif error:
			print("[OnlineUpdateCheck][getFeedsBool] Check already in progress")
			return "inprogress"
		elif self.feedstatus == "updating":
			print("[OnlineUpdateCheck][getFeedsBool] Feeds Updating")
			return "updating"
		elif self.feedstatus in ("stable", "unstable", "unknown", "alien", "developer"):
			print("[OnlineUpdateCheck][getFeedsBool]", self.feedstatus)
			return self.feedstatus

	def getFeedsErrorMessage(self):
		global error
		if self.feedstatus == -2:
			return _("Your %s %s has no internet access, please check your network settings and make sure you have network cable connected and try again.") % (SystemInfo["displaybrand"], SystemInfo["machinename"])
		elif self.feedstatus == -3:
			return _("Your %s %s has no network access, please check your network settings and make sure you have network cable connected and try again.") % (SystemInfo["displaybrand"], SystemInfo["machinename"])
		elif self.feedstatus == 404:
			return _("Your %s %s is not able to connect to the feeds, please try again later. If this persists please report on the OpenBh forum at openbh.net") % (SystemInfo["displaybrand"], SystemInfo["machinename"])
		elif self.feedstatus in ("updating", 403):
			return _("Sorry feeds are down for maintenance, please try again later. If this issue persists please check openbh.net")
		elif "error" in self.feedstatus.lower():  # python exceptions
			return _("There has been a '%s', please try again later. If this persists please report on the OpenBh forum at openbh.net") % self.feedstatus
		elif error:
			return _("There has been an error, please try again later. If this persists please report on the OpenBh forum at openbh.net")

	def startCheck(self):
		global error
		error = 0
		self.updating = True
		self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)

	def ipkgCallback(self, event, param):
		config.softwareupdate.updatefound.setValue(False)
		if event == IpkgComponent.EVENT_ERROR:
			global error
			error += 1
		elif event == IpkgComponent.EVENT_DONE:
			if self.updating:
				self.updating = False
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
			elif self.ipkg.currentCommand == IpkgComponent.CMD_UPGRADE_LIST:
				self.total_packages = len(self.ipkg.getFetchedList())
				if self.total_packages and (SystemInfo["imagetype"] != "release" or (config.softwareupdate.updateisunstable.value == 1 and config.softwareupdate.updatebeta.value) or config.softwareupdate.updateisunstable.value == 0):
					print(("[OnlineUpdateCheck][ipkgCallback] %s Updates available" % self.total_packages))
					config.softwareupdate.updatefound.setValue(True)
		pass


feedsstatuscheck = FeedsStatusCheck()


class OnlineUpdateCheckPoller:
	def __init__(self):
		# Init Timer
		self.timer = eTimer()

	# Class variables
	MIN_INITIAL_DELAY = 40 * 60  # Wait at least 40 mins
	checktimer_Notifier_Added = False

	# Add optional args to start(), as it is now a callback from addNotifier
	# so will have one when called from there.
	def start(self, *args, **kwargs):
		if self.onlineupdate_check not in self.timer.callback:
			self.timer.callback.append(self.onlineupdate_check)

		# This will get start re-run on any change to the interval setting
		# so the next-timer will be suitably updated...
		# ...but only add one of them!!!
		if not self.checktimer_Notifier_Added:
			config.softwareupdate.checktimer.addNotifier(self.start, initial_call=False, immediate_feedback=False)
			self.checktimer_Notifier_Added = True
			minimum_delay = self.MIN_INITIAL_DELAY
		else:  # we been here before, so this is *not* start-up
			minimum_delay = 60  # 1 minute

		last_run = config.softwareupdate.updatelastcheck.getValue()
		gap = config.softwareupdate.checktimer.value * 3600
		delay = last_run + gap - int(time())

		# Set-up the minimum delay, which is greater on the first boot-time pass.
		# Also check that we aren't setting a delay that is more than the
		# configured frequency of checks, which caters for mis-/un-set system
		# clocks.
		if delay < minimum_delay:
			delay = minimum_delay
		if delay > gap:
			delay = gap
		self.timer.startLongTimer(delay)

	def stop(self):
		if self.version_check in self.timer.callback:
			self.timer.callback.remove(self.onlineupdate_check)
		self.timer.stop()

	def onlineupdate_check(self):
		if config.softwareupdate.check.value:
			Components.Task.job_manager.AddJob(self.createCheckJob())
		self.timer.startLongTimer(config.softwareupdate.checktimer.value * 3600)

		# Record the time of this latest check
		config.softwareupdate.updatelastcheck.setValue(int(time()))
		config.softwareupdate.updatelastcheck.save()

	def createCheckJob(self):
		job = Components.Task.Job(_("OnlineVersionCheck"))
		task = Components.Task.PythonTask(job, _("Checking for Updates..."))
		task.work = self.JobStart
		task.weighting = 1
		return job

	def JobStart(self):
		config.softwareupdate.updatefound.setValue(False)
		if feedsstatuscheck.getFeedsBool() in ("alien", "developer", "stable", "unstable"):
			print("[OnlineUpdateCheckPoller] Starting background check.")
			feedsstatuscheck.startCheck()
		else:
			print("[OnlineUpdateCheckPoller] No feeds found, skipping check.")


# Create a callable instance...
onlineupdatecheckpoller = OnlineUpdateCheckPoller()


class VersionCheck:
	def __init__(self):
		pass

	def getStableUpdateAvailable(self):
		if config.softwareupdate.updatefound.value and config.softwareupdate.check.value:
			if SystemInfo["imagetype"] != "release" or config.softwareupdate.updateisunstable.value == 0:
				print("[OnlineVersionCheck] New Release updates found")
				return True
			else:
				print("[OnlineVersionCheck] skipping as unstable is not wanted")
				return False
		else:
			return False

	def getUnstableUpdateAvailable(self):
		if config.softwareupdate.updatefound.value and config.softwareupdate.check.value:
			if SystemInfo["imagetype"] != "release" or (config.softwareupdate.updateisunstable.value == 1 and config.softwareupdate.updatebeta.value):
				print("[OnlineVersionCheck] New Experimental updates found")
				return True
			else:
				print("[OnlineVersionCheck] skipping as beta is not wanted")
				return False
		else:
			return False


versioncheck = VersionCheck()


def kernelMismatch():
	# returns True if a kernal mismatch is found. i.e. STB kernel does not match feeds kernel
	import zlib
	import re

	kernelversion = about.getKernelVersionString().strip()
	if kernelversion == "unknown":
		print("[OnlineUpdateCheck][kernelMismatch] unable to retrieve kernel version from STB")
		return False

	uri = "%s/%s/Packages.gz" % (SystemInfo["feedsurl"], SystemInfo["model"])
	try:
		req = Request(uri)
		d = urlopen(req)
		gz_data = d.read()
	except:
		print("[OnlineUpdateCheck][kernelMismatch] error fetching %s" % uri)
		return False

	try:
		packages = zlib.decompress(gz_data, 16 + zlib.MAX_WBITS)
	except:
		print("[OnlineUpdateCheck][kernelMismatch] failed to decompress gz_data")
		return False

	pattern = "kernel-([0-9]+[.][0-9]+[.][0-9]+)"
	# print("[OnlineUpdateCheck][kernelMismatch] packages=%s" % (packages))
	packages = packages.decode()
	matches = re.findall(pattern, packages)
	if matches:
		match = sorted(matches, key=lambda s: list(map(int, s.split("."))))[-1]
		if match != kernelversion:
			print("[OnlineUpdateCheck][kernelMismatch] kernel mismatch found. STB kernel=%s, feeds kernel=%s" % (kernelversion, match))
			return True

	print("[OnlineUpdateCheck][kernelMismatch] no kernel mismatch found")
	return False


def statusMessage():
	# returns message if status message is found, else False.
	# status-message.php goes in the root folder of the feeds webserver
	uri = "http://%s/status-message.php?machine=%s&version=%s&build=%s" % (SystemInfo["feedsurl"].split("/")[2], SystemInfo["boxtype"], SystemInfo["imageversion"], SystemInfo["imagebuild"])
	try:
		req = Request(uri)
		d = urlopen(req)
		message = d.read().decode()
	except:
		print("[OnlineUpdateCheck][statusMessage] %s could not be fetched" % uri)
		return False

	if message:
		return message
	return False
