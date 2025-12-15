# Piplayer
A modular headless lightweight player for SBCs (Raspberry etc) with low cpu power in mind


## Install

It is not recommended to use conda as environment

Run
```
sudo bash install.sh
```

## Compatible Formats

### Audio

- wav (recommended)
- mp3

### Sequences

- mid (with multiple tracks)


## How to use

If using midi files to control sequences, first run:

```
piplayer-setup myfile.mid
```

And for playback run:

```
piplayer beat.wav --sequence seq.mid --loop --gui -c config.json
```


## Sync modes
```
piplayer sound.wav -s lights.mid --gui --mode master
piplayer sound.wav -s lights.mid --gui --mode follower
```


## Developer notes:

**TODO:**
- Fix GUI, it doesn't work in a solid way

Install with this for development
```
sudo pip install -e .
```
If using new versions of PiOS and you want to ignore the venv warnings use this flag
```
sudo pip install --break-system-packages -e .
```

## Known issues
- It is reported to not work with Python 3.13, stay below 3.12
