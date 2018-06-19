# SpotRec

Python script to record the audio of the Spotify desktop client using FFmpeg
and PulseAudio

AUR: https://aur.archlinux.org/packages/spotrec/



## Usage

If you use the AUR package,
you can simply run:

```
spotrec
```

If you have a GNU/Linux distribution with a different package manager system,
run:

```
python3 spotrec.py
```

or

```
./spotrec.py
```


### Example

First of all run spotify

Optional: to avoid annoing ads you can use
[Spotify-AdKiller](https://github.com/SecUpwN/Spotify-AdKiller):

```
./spotify-wrapper.sh
```

Then you can run the python script which will record the music:

```
./spotrec.py -o ./my_song_dir --skip-intro --tmp-file
```

Check the  pulseaudio configuration:

```
pavucontrol
```

Pay attention to the red circles, everything else is muted and with volume set
to 0%

![playback tab](https://github.com/Bleuzen/SpotRec/raw/master/img/pavucontrol_playback_tab.jpeg)

Note: actually "Lavf..." will appear after you start playing a song

![recording tab](https://github.com/Bleuzen/SpotRec/raw/master/img/pavucontrol_recording_tab.jpeg)

![output devices tab](https://github.com/Bleuzen/SpotRec/raw/master/img/pavucontrol_output_devices_tab.jpeg)

![input devices tab](https://github.com/Bleuzen/SpotRec/raw/master/img/pavucontrol_input_devices_tab.jpeg)

![configuration tab](https://github.com/Bleuzen/SpotRec/raw/master/img/pavucontrol_configuration_tab.jpeg)

Finally start playing whatever you want


## Hints

- Disable volume normalization in the Spotify Client

- Do not change the volume during recording

- Use Audacity for post processing

  * because SpotRec records a little longer at the end to ensure that nothing is missing of the song. But sometimes this also includes the beginning of the next song. So you should use Audacity to cut the audio to what you want. From Audacity you can also export it to the format you like (ogg/mp3/...).


## Troubleshooting

Start the script with the debug flag:

```
./spotrec.py --debug
```

If one of the following scenarios happens:

* you do not see something like the ffmpeg output, which should appear right
  few seconds after the song start

```
# what you should see when ffmpeg is recording ...
size=56400kB time=00:00:04.15 bitrate= 130.7kbits/s speed=1x
```

* you do not see any "Lavf..." in the pavucontrol
  [recording tab](https://github.com/Bleuzen/SpotRec/raw/master/img/pavucontrol_recording_tab.jpeg)
* you get a stacktrace ending with:

```
ValueError: invalid literal for int() with base 10: 'nput'
```

I would suggest you to:

* quickly press the "next song button" and then the "previous song button" in
  the spotify client
* stop everything and start over, after some tries it usually works :)


**Note: sometimes spotify detects when the user does not interact with the
application for a long time (more or less an hour) and starts looping over a
song, to avoid this scenario I would suggest to keep interacting with the
spotify client.**
