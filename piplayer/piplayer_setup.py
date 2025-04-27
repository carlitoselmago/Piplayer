# piplayer_setup.py
import json
import argparse
from piplayer.modules.sequence_loader import SequenceLoader


# Available output types
PROTOCOL_CHOICES = {
    1: "GPIO",
    2: "DMX",
    # Future: 3: "SPI", etc.
}

def setup_configuration(midi_file: str, output_file: str) -> None:
    print(f"Loading MIDI file: {midi_file}")
    sequence = SequenceLoader(midi_file)

    if not sequence.track_names:
        print("No tracks found in the MIDI file!")
        return

    config = {"track_mappings": {}}

    print("\nTracks found:")
    for idx, track in enumerate(sequence.track_names):
        track_display = track if track.strip() else "--empty--"
        print(f"[{idx}] {track_display}")

    print("\nAssign output type for each track:")

    for track in sequence.track_names:
        track_display = track if track.strip() else "--empty--"
        print(f"\nTrack: {track_display}")
        print("[0] None (ignore this track)")
        for num, proto in PROTOCOL_CHOICES.items():
            print(f"[{num}] {proto}")
        while True:
            try:
                choice = int(input("Select protocol number: "))
                if choice == 0:
                    # Ignore this track
                    break
                elif choice in PROTOCOL_CHOICES:
                    config["track_mappings"][track_display] = PROTOCOL_CHOICES[choice]
                    break
                else:
                    print("Invalid choice. Please enter a valid number.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    # Save to JSON
    with open(output_file, "w") as f:
        json.dump(config, f, indent=4)

    print(f"\n✅ Configuration saved to {output_file}")

# -------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="PiPlayer Setup Tool")
    parser.add_argument("midi_file", help="Path to the MIDI (.mid) file")
    parser.add_argument("-o", "--output", default="config.json",
                        help="Path to save the config (default: config.json)")
    args = parser.parse_args()

    setup_configuration(args.midi_file, args.output)

if __name__ == "__main__":
    main()
