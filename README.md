# SpotRec

Python script to record the audio of the Spotify desktop client using FFmpeg
and PulseAudio

AUR: https://aur.archlinux.org/packages/spotrec/



## Usage

If you have a GNU/Linux distribution with a different package manager system,
you can simply run:

```
python3 ./spotrec.py
```



### Example

What follows is my favourite configuration, your taste / software / hardware
might differ...

First of all run spotify, to avoid annoing ads I would recommend you
[Spotify-AdKiller](https://github.com/SecUpwN/Spotify-AdKiller):

```
./spotify-wrapper.sh
```

Then you can run the python script which will record the music:

```
./spotrec.py --debug --mute-sink -o ./my_song_dir --skip-intro --tmp-file --underscored-filenames
```

Check the  pulseaudio configuration:

```
pavucontrol
```

Pay attention to the red circles, everything else is muted and with volume set
to 0%

![playback tab](https://github.com/TheJena/SpotRec/raw/master/img/pavucontrol_playback_tab.jpeg)

Note: actually "Lavf..." will appear after you start playing a song

![recording tab](https://github.com/TheJena/SpotRec/raw/master/img/pavucontrol_recording_tab.jpeg)

![output devices tab](https://github.com/TheJena/SpotRec/raw/master/img/pavucontrol_output_devices_tab.jpeg)

![input devices tab](https://github.com/TheJena/SpotRec/raw/master/img/pavucontrol_input_devices_tab.jpeg)

![configuration tab](https://github.com/TheJena/SpotRec/raw/master/img/pavucontrol_configuration_tab.jpeg)

Finally start playing whatever you want



## Troubleshooting

If one of the following scenarios happens:

* you do not see something like the ffmpeg output, which should appear right
  few seconds after the song start

```
# what you should see when ffmpeg is recording ...
size=56400kB time=00:00:04.15 bitrate= 130.7kbits/s speed=1x
```

* you do not see any "Lavf..." in the pavucontrol
  [recording tab](https://github.com/TheJena/SpotRec/raw/master/img/pavucontrol_recording_tab.jpeg)
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
