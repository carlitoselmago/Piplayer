import simpleaudio as sa

wave_obj = sa.WaveObject.from_wave_file("beat_fixed.wav")  # open WAV directly
#sprint(f"Length (approx): {wave_obj.num_frames / wave_obj.sample_rate:.2f} seconds")

play_obj = wave_obj.play()
play_obj.wait_done()