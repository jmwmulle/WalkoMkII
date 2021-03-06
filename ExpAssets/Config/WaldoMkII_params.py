import random
# KlibsTesting Param overrides
#
# Any param that is commented out by default is either deprecated or else not yet implemented--don't uncomment or use
#
#########################################
# Available Hardware
#########################################
eye_tracker_available = True
eye_tracking = True
labjack_available = False
labjacking = False
#
#########################################
# Environment Aesthetic Defaults
#########################################
default_fill_color = (255, 255, 255, 255)
default_color = (45, 45, 45, 45)
default_response_color = default_color
default_input_color = default_color
default_font_size = 28
default_font_name = 'Frutiger'
default_timeout_message = "Too slow!"
#
#########################################
# EyeLink Sensitivities
#########################################
saccadic_velocity_threshold = 20
saccadic_acceleration_threshold = 5000
saccadic_motion_threshold = 0.15
#
fixation_size = 1,  # deg of visual angle
box_size = 1,  # deg of visual angle
cue_size = 1,  # deg of visual angle
cue_back_size = 1,  # deg of visual angle
#
#########################################
# Experiment Structure
#########################################
collect_demographics = True
practicing = False
trials_per_block = 72
blocks_per_experiment = 3
trials_per_participant = 0
#
#########################################
# Development Mode Settings
#########################################
dm_suppress_debug_pane = False
dm_auto_threshold = True

#
#########################################
# Data Export Settings
#########################################
data_columns = None
default_participant_fields = [["userhash", "participant"], "sex", "age", "handedness"]
default_participant_fields_sf = [["userhash", "participant"], "random_seed", "sex", "age", "handedness"]

#
#########################################
# Demographics Questions
#########################################
# Note: This list must supply all columns in the configured Participants table except:
# 	- id
# 	- participant id
# 	- random_seed
#	- klibs_commit (if present)
#	- created
# These columns must be present in the participants table (except klibs_commit) and are supplied automatically by klibs
demographic_questions = [
	['sex', "What is your sex? \nAnswer with:  (m)ale,(f)emale", ('m', 'M', 'f', 'F'), 'str', random.choice(['m', 'f'])],
	['handedness', "Are right-handed, left-handed or ambidextrous? \nAnswer with (r)ight, (l)eft or (a)mbidextrous.",
	 ('r', 'R', 'l', 'L', 'a', 'A'), 'str', 'r'],
	['age', 'What is  your age?', None, 'int', -1]
]

#
#########################################
# PROJECT-SPECIFIC VARS
#########################################
# disc persistence not yet ready; still buggy; leave False
persist_to_exit_saccade = False #  else disc_n will me removed simultaneously with the presentation of disc_n+1

fixation_interval = 1500  # ms
disc_timeout_interval = 1000  # ms
drift_correct_initial_persist = 1000  # ms
final_disc_timeout_interval = 2000  # ms
inter_disc_interval = 300  # False or ms, min time after disc_n presented before disc_n+1 can be shown
fixation_top = [None, None]
fixation_central = [None, None]
fixation_bottom = [None, None]
exp_meta_factors = {"fixation": [fixation_top, fixation_central, fixation_bottom]}

