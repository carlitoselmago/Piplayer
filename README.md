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
piplayer beat.wav --sequence seq.mid --loop --gui
```

## Developer notes:

**TODO:**
- Fix GUI, it doesn't work in a solid way

Install with this for development
```
sudo pip install -e .
```