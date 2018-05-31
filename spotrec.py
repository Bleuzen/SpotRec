#!/usr/bin/python3

import dbus
from dbus.exceptions import DBusException
import dbus.mainloop.glib
from gi.repository import GLib

from threading import Thread
import subprocess
import time
import sys
import shutil
import re
import os
import argparse
import traceback
import logging

# Deps:
# 'python'
# 'python-dbus'
# 'ffmpeg'
# 'gawk': awk in command to get sink input id of spotify
# 'pulseaudio': sink control stuff
# 'bash': shell commands

app_name = "SpotRec"
app_version = "0.7.1"

# Settings with Defaults
_debug_logging = False
_skip_intro = False
_no_pa_sink = False
_mute_pa_sink = False
_output_directory = "Audio"
_filename_pattern = "{trackNumber} - {artist} - {title}"
_tmp_file = False
_underscored_filenames = False

# Hard-coded settings
_pulse_sink_name = "spotrec"
_recording_time_before_song = 0.25
_recording_time_after_song = 2.25
_playback_time_before_seeking_to_beginning = 4.5
_shell_executable = "/bin/bash"  # Default: "/bin/sh"
_shell_encoding = "utf-8"

# Variables that change during runtime
is_script_paused = False
is_first_playing = True


def main():
    handle_command_line()

    if not _skip_intro:
        print(app_name + " v" + app_version)
        print("This is an very early and experimental version. Expect some bugs ;)")
        print('Recordings are save to a directory called "Audio" in your current working directory by default. Existing files will be overridden.')
        print('Use --help as argument to see all options.')
        print()
        print("Disclaimer:")
        print('This software is for "educational" purposes only. No responsibility is held or accepted for misuse.')
        print()

    init_log()

    # Create the output directory
    os.makedirs(_output_directory, exist_ok=True)

    # Init Spotify DBus listener
    global _spotify
    _spotify = Spotify()

    # Load PulseAudio sink if wanted
    if not _no_pa_sink:
        PulseAudio.load_sink()

    _spotify.try_to_move_to_sink_if_needed()

    # Keep the main thread alive (to be able to handle KeyboardInterrupt)
    while True:
        time.sleep(1)


def doExit():
    log.info(f"[{app_name}] Shutting down ...")

    # Stop Spotify DBus listener
    _spotify.quit_glib_loop()

    # Disable _tmp_file to not rename the last recording which is uncomplete at this state
    global _tmp_file
    _tmp_file = False

    # Kill all FFmpeg subprocesses
    FFmpeg.killAll()

    # Unload PulseAudio sink if it was loaded
    if not _no_pa_sink:
        PulseAudio.unload_sink()

    log.info(f"[{app_name}] Bye")

    # Have to use os exit here, because otherwise GLib would print a strange error message
    os._exit(0)
    #sys.exit(0)


def handle_command_line():
    global _debug_logging
    global _skip_intro
    global _no_pa_sink
    global _mute_pa_sink
    global _output_directory
    global _filename_pattern
    global _tmp_file
    global _underscored_filenames

    #parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser = argparse.ArgumentParser(description=app_name + " v" + app_version, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-d", "--debug", help="Print a little more", action="store_true", default=_debug_logging)
    parser.add_argument("-s", "--skip-intro", help="Skip the intro message", action="store_true", default=_skip_intro)
    parser.add_argument("-n", "--no-sink", help="Don't create an extra PulseAudio sink for recording", action="store_true", default=_no_pa_sink)
    parser.add_argument("-m", "--mute-sink", help="Don't play sink output on your main sink", action="store_true", default=_mute_pa_sink)
    parser.add_argument("-o", "--output-directory", help="Where to save the recordings\n"
                                                         "Default: " + _output_directory, default=_output_directory)
    parser.add_argument("-p", "--filename-pattern", help="A pattern for the file names of the recordings\n"
                                                         "Available: {artist}, {album}, {trackNumber}, {title}\n"
                                                         "Default: \"" + _filename_pattern + "\"", default=_filename_pattern)
    parser.add_argument("-t", "--tmp-file", help="Use a temporary hidden file during recording and rename it only if the recording has been completed succesfully", action="store_true", default=_tmp_file)
    parser.add_argument("-u", "--underscored-filenames", help="Force the file names to have underscores instead of whitespaces", action="store_true", default=_underscored_filenames)

    args = parser.parse_args()

    _debug_logging = args.debug

    _skip_intro = args.skip_intro

    _no_pa_sink = args.no_sink

    _mute_pa_sink = args.mute_sink

    _filename_pattern = args.filename_pattern

    _output_directory = args.output_directory

    _tmp_file = args.tmp_file

    _underscored_filenames = args.underscored_filenames


def init_log():
    global log
    log = logging.getLogger()

    if _debug_logging:
        FORMAT = '%(asctime)-15s - %(levelname)s - %(message)s'
        log.setLevel(logging.DEBUG)
    else:
        FORMAT = '%(message)s'
        log.setLevel(logging.INFO)

    logging.basicConfig(format=FORMAT)

    log.debug("Logger initialized")


class Spotify:
    dbus_dest = "org.mpris.MediaPlayer2.spotify"
    dbus_path = "/org/mpris/MediaPlayer2"
    mpris_player_string = "org.mpris.MediaPlayer2.Player"

    playbackstatus_playing = "Playing"
    playbackstatus_paused = "Paused"

    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        try:
            bus = dbus.SessionBus()
            player = bus.get_object(self.dbus_dest, self.dbus_path)
            self.iface = dbus.Interface(player, "org.freedesktop.DBus.Properties")
            self.metadata = self.iface.Get(self.mpris_player_string, "Metadata")
        except DBusException as e:
            log.error("Failed to connect to Spotify. (Maybe it's not running yet?)")
            sys.exit(1)
            pass

        self.track = self.get_track(self.metadata)
        self.trackid = self.metadata.get(dbus.String(u'mpris:trackid'))
        self.playbackstatus = self.iface.Get(self.mpris_player_string, "PlaybackStatus")
        self.is_playing = (self.playbackstatus == self.playbackstatus_playing)

        self.iface.connect_to_signal("PropertiesChanged", self.on_playing_uri_changed)

        class DBusListenerThread(Thread):
            def run(self2):
                # Run the GLib event loop to process DBus signals as they arrive
                self.glibloop = GLib.MainLoop()
                self.glibloop.run()

                # run() blocks this thread. This gets printed after it's dead.
                log.info(f"[{app_name}] GLib Loop thread killed")

        dbuslistener = DBusListenerThread()
        dbuslistener.start()

        log.info(f"[{app_name}] Spotify DBus listener started")

        log.info(f"[{app_name}] Current song: " + self.track)
        log.info(f"[{app_name}] Current state: " + self.playbackstatus)

    # TODO: this is a dirty solution (uses cmdline instead of python for now)
    def send_dbus_cmd(self, cmd):
        Shell.run('dbus-send --print-reply --dest=' + self.dbus_dest + ' ' + self.dbus_path + ' ' + self.mpris_player_string + '.' + cmd)

    def quit_glib_loop(self):
        self.glibloop.quit()

        log.info(f"[{app_name}] Spotify DBus listener stopped")

    def get_track(self, metadata):
        if _underscored_filenames:
            filename_pattern = re.sub(" - ", "__", _filename_pattern)
        else:
            filename_pattern = _filename_pattern

        ret = str(filename_pattern.format(
            artist=metadata.get(dbus.String(u'xesam:artist'))[0],
            album=metadata.get(dbus.String(u'xesam:album')),
            trackNumber=str(metadata.get(dbus.String(u'xesam:trackNumber'))).zfill(2),
            title=metadata.get(dbus.String(u'xesam:title')),
            ))

        if _underscored_filenames:
            ret = ret.replace(".", "").lower()
            ret = re.sub("[\s\-\[\]()']+", "_", ret)
            ret = re.sub("__+", "__", ret)

        return ret

    def start_record(self):
        # Start new recording in new Thread
        class RecordThread(Thread):
            def run(self2):
                global is_script_paused

                # Save current trackid to check later if it is still the same song playing (to avoid a bug when user skipped a song)
                self2.trackid_when_thread_started = self.trackid

                # Stop the recording before
                # Use copy() to not change the list during this method runs
                self.stop_old_recording(FFmpeg.instances.copy())

                # This is currently the only way to seek to the beginning (let it Play for some seconds, Pause and send Previous)
                time.sleep(_playback_time_before_seeking_to_beginning)

                # Check if still the same song is still playing, return if not
                if self2.trackid_when_thread_started != self.trackid:
                    return

                # Spotify pauses when the playlist ended. Don't start a recording / return in this case.
                if not self.is_playing:
                    log.info(f"[{app_name}] Spotify is paused. Maybe the current album or playlist has ended.")

                    # TODO: do we need it anymore?
                    if not is_script_paused:
                        doExit()

                    return

                log.info(f"[{app_name}] Starting recording")

                # Set is_script_paused to not trigger wrong Pause event in playbackstatus_changed()
                is_script_paused = True
                self.send_dbus_cmd("Pause")
                time.sleep(0.25)
                is_script_paused = False
                self.send_dbus_cmd("Previous")

                # Start FFmpeg recording
                ff = FFmpeg()
                ff.record(self.track)

                # Give FFmpeg some time to start up before starting the song
                time.sleep(_recording_time_before_song)

                # Play the track
                self.send_dbus_cmd("Play")

        record_thread = RecordThread()
        record_thread.start()

    def stop_old_recording(self, instances):
        # Stop the oldest FFmpeg instance (from recording of song before) (if one is running)
        if len(instances) > 0:
            class OverheadRecordingStopThread(Thread):
                def run(self):
                    # Record a little longer to not miss something
                    time.sleep(_recording_time_after_song)

                    # Stop the recording
                    instances[0].stop_blocking()

            overhead_recording_stop_thread = OverheadRecordingStopThread()
            overhead_recording_stop_thread.start()

    # This gets called whenever Spotify sends the playingUriChanged signal
    def on_playing_uri_changed(self, Player, three, four):
        global iface
        global track
        global home

        #log.debug("uri changed event")

        # Update Metadata
        self.metadata = self.iface.Get(self.mpris_player_string, "Metadata")

        # Update track & trackid

        self.trackid2 = self.metadata.get(dbus.String(u'mpris:trackid'))
        if self.trackid != self.trackid2:
            # Update trackid
            self.trackid = self.trackid2
            # Update track name
            self.track = self.get_track(self.metadata)
            # Trigger event method
            self.playing_song_changed()

        # Update playback status

        global playbackstatus

        self.playbackstatus2 = self.iface.Get(Player, "PlaybackStatus")

        if self.playbackstatus != self.playbackstatus2:
            self.playbackstatus = self.playbackstatus2
            self.is_playing = (self.playbackstatus == self.playbackstatus_playing)

            self.playbackstatus_changed()

    def playing_song_changed(self):
        log.info("[Spotify] Song changed: " + self.track)

        self.start_record()

    def playbackstatus_changed(self):
        log.info("[Spotify] State changed: " + self.playbackstatus)

        self.try_to_move_to_sink_if_needed()

    def try_to_move_to_sink_if_needed(self):
        if self.playbackstatus == "Playing":
            global is_first_playing
            if is_first_playing:
                is_first_playing = False
                if not _no_pa_sink:
                    PulseAudio.move_spotify_to_own_sink()


class FFmpeg:
    instances = []

    def record(self, filename):
        if _no_pa_sink:
            self.pulse_input = "default"
        else:
            self.pulse_input = _pulse_sink_name + ".monitor"

        if _tmp_file:
            # Use a dot as filename prefix to hide the file until the recording was successful
            self.tmp_file_prefix = "."
            self.filename = self.tmp_file_prefix + filename + ".flac"
        else:
            self.filename = filename + ".flac"

        # self.process = Shell.Popen('ffmpeg -y -f alsa -ac 2 -ar 44100 -i pulse -acodec flac "' + _output_directory + "/" + filename + '.flac"')
        # Options:
        #  "-hide_banner": to short the debug log a little
        #  "-y": to overwrite existing files
        self.process = Shell.Popen('ffmpeg -hide_banner -y -f pulse -ac 2 -ar 44100 -i ' + self.pulse_input + ' -acodec flac "' + _output_directory + "/" + self.filename + '"')

        self.pid = str(self.process.pid)

        self.instances.append(self)

        log.info(f"[FFmpeg] [{self.pid}] Recording started")

    # The blocking version of this method waits until the process is dead
    def stop_blocking(self):
        # Remove from instances list (and terminate)
        if self in self.instances:
            self.instances.remove(self)

            # Send CTRL_C
            self.process.terminate()

            log.info(f"[FFmpeg] [{self.pid}] terminated")

            # Sometimes this is not enough and ffmpeg survives, so we have to kill it after some time
            time.sleep(1)

            if self.process.poll() == None:
                # None means it has no return code (yet), with other words: it is still running

                self.process.kill()

                log.info(f"[FFmpeg] [{self.pid}] killed")
            else:
                if _tmp_file:
                    tmp_file = os.path.join(_output_directory, self.filename)
                    new_file = os.path.join(_output_directory,
                                            self.filename[len(self.tmp_file_prefix):])
                    if os.path.exists(tmp_file):
                        shutil.move(tmp_file, new_file)
                        log.debug(f"[FFmpeg] [{self.pid}] Successfully renamed {self.filename}")
                    else:
                        log.warning(f"[FFmpeg] [{self.pid}] Failed renaming {self.filename}")

            # Remove process from memory (and don't left a ffmpeg 'zombie' process)
            self.process = None

    # Kill the process in the background
    def stop(self):
        class KillThread(Thread):
            def run(self2):
                self.stop_blocking()

        kill_thread = KillThread()
        kill_thread.start()

    @staticmethod
    def killAll():
        log.info("[FFmpeg] Killing all instances")

        # Run as long as list ist not empty
        while FFmpeg.instances:
            FFmpeg.instances[0].stop_blocking()

        log.info("[FFmpeg] All instances killed")


class Shell:
    @staticmethod
    def run(cmd):
        # 'run()' waits until the process is done
        if _debug_logging:
            return subprocess.run(cmd, stdin=None, shell=True, executable=_shell_executable, encoding=_shell_encoding)
        else:
            with open("/dev/null", "w") as devnull:
                return subprocess.run(cmd, stdin=None, stdout=devnull, stderr=devnull, shell=True, executable=_shell_executable, encoding=_shell_encoding)

    @staticmethod
    def Popen(cmd):
        # 'Popen()' continues running in the background
        if _debug_logging:
            return subprocess.Popen(cmd, stdin=None, shell=True, executable=_shell_executable, encoding=_shell_encoding)
        else:
            with open("/dev/null", "w") as devnull:
                return subprocess.Popen(cmd, stdin=None, stdout=devnull, stderr=devnull, shell=True, executable=_shell_executable, encoding=_shell_encoding)

    @staticmethod
    def check_output(cmd):
        out = subprocess.check_output(cmd, shell=True, executable=_shell_executable, encoding=_shell_encoding)
        return out
        # when not using 'encoding=' -> out.decode()
        # but since it is set, decode() ist not needed anymore, just return out


class PulseAudio:
    sink_id = ""

    @staticmethod
    def load_sink():
        log.info(f"[{app_name}] Creating pulse sink")

        if _mute_pa_sink:
            PulseAudio.sink_id = Shell.check_output('pactl load-module module-null-sink sink_name=' + _pulse_sink_name + ' sink_properties=device.description="' + _pulse_sink_name + '" rate=44100 channels=2')
        else:
            PulseAudio.sink_id = Shell.check_output('pactl load-module module-remap-sink sink_name=' + _pulse_sink_name + ' sink_properties=device.description="' + _pulse_sink_name + '" rate=44100 channels=2 remix=no')
            # To use another master sink where to play:
            # pactl load-module module-remap-sink sink_name=spotrec sink_properties=device.description="spotrec" master=MASTER_SINK_NAME channels=2 remix=no

    @staticmethod
    def unload_sink():
        log.info(f"[{app_name}] Unloading pulse sink")
        Shell.run('pactl unload-module ' + PulseAudio.sink_id)

    @staticmethod
    def get_spotify_sink_input_id():
        application_name = "spotify"
        cmdout = Shell.check_output("pactl list sink-inputs | awk '{print tolower($0)};' | awk '/ #/ {print $2} /application.name = \"" + application_name + "\"/ {print $3};'")
        index = -1
        last = -1

        for line in cmdout.split('\n'):
            if line == '"' + application_name + '"':
                index = last[1:]
                break
            last = line

        return index

    @staticmethod
    def move_spotify_to_own_sink():
        class MoveSpotifyToSinktThread(Thread):
            def run(self):
                spotify_id = int(PulseAudio.get_spotify_sink_input_id())

                if spotify_id > -1:
                    exit_code = Shell.run("pactl move-sink-input " + str(spotify_id) + " " + _pulse_sink_name).returncode

                    if exit_code == 0:
                        log.info(f"[{app_name}] Moved Spotify to own sink")
                    else:
                        log.warning(f"[{app_name}] Failed to move Spotify to own sink")

        move_spotify_to_sink_thread = MoveSpotifyToSinktThread()
        move_spotify_to_sink_thread.start()


if __name__ == "__main__":
    # Handle exit (not print error when pressing Ctrl^C)
    try:
        main()
    except KeyboardInterrupt:
        doExit()
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
    sys.exit(0)
