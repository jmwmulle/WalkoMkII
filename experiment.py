import klibs

__author__ = "Jonathan Mulle"

from klibs import KLEyeLink
from klibs.KLExceptions import *
from klibs.KLUtilities import *
import klibs.KLDraw as kld
from klibs.KLNumpySurface import NumpySurface as ns
from random import  choice, randrange
from klibs.KLEventInterface import EventTicket as ET
from klibs.KLMixins import BoundaryInspector
from copy import copy

LOC = "location"
AMP = "amplitude"
ANG = "angle"
NEW = "new"
OLD = "old"
RED = [236, 88, 64, 255]
WHITE = [255,255,255,255]
GREY = [125,125,125,255]
BLACK = [0,0,0,255]
BG_ABSENT = "absent"
BG_PRESENT = "present"
BG_INTERMITTENT = "intermittent"

class WaldoMkII(klibs.Experiment, BoundaryInspector):
	debug_mode = True
	max_amplitude_deg = 6  # degrees of visual angle
	min_amplitude_deg = 3  # degrees of visual angle
	max_amplitude = None  # px
	min_amplitude = None  # px
	min_saccades = 5
	max_saccades = 12
	disc_diameter_deg = 1
	disc_diameter = None
	search_disc_proto = None
	search_disc_color = BLACK
	display_margin = None  # ie. the area in which targets may not be presented
	allow_intermittent_bg = True
	fixation_boundary_tolerance = 3  # scales boundary (not image) if drift_correct target too small to fixate
	disc_boundary_tolerance = 0.5  # scales boundary (not image) if drift_correct target too small to fixate
	looked_away_msg = None
	eyes_moved_message = None

	# trial vars
	locations = []
	trial_type = None
	backgrounds = {}
	bg = None
	bg_state = None
	saccade_count = None
	frame_size = "1920x1200"
	#frame_size = "1024x768"
	n_back = None  # populated from config
	angle = None   # populated from config
	n_back_index = None
	inter_disc_event_label = None  # set after each disc has been saccaded to

	def __init__(self, *args, **kwargs):
		super(WaldoMkII, self).__init__(*args, **kwargs)
		self.max_amplitude = deg_to_px(self.max_amplitude_deg)
		self.min_amplitude = deg_to_px(self.min_amplitude_deg)
		self.disc_diameter = deg_to_px(self.disc_diameter_deg)
		self.disc_boundary_tolerance = deg_to_px(self.disc_boundary_tolerance)
		self.display_margin = int(self.disc_diameter * 1.5)
		self.search_disc_proto = kld.Annulus(self.disc_diameter, int(self.disc_diameter * 0.25), (2,WHITE), BLACK)
		if Params.inter_disc_interval and Params.persist_to_exit_saccade:
			raise RuntimeError("Params.inter_disc_interval and Params.persist_to_exit_saccade cannot both be set.")

	def setup(self):
		r = kld.drift_correct_target().width * self.fixation_boundary_tolerance
		self.eyelink.add_gaze_boundary("trial_fixation", [Params.screen_c, r], CIRCLE_BOUNDARY)
		self.fill(Params.default_fill_color)
		self.text_manager.add_style("msg", 64)
		self.text_manager.add_style("err", 64, WHITE)
		self.text_manager.add_style("tny", 12)
		self.looked_away_msg = self.message("Looked away too soon.", "err", blit=False)
		self.message("Loading, please hold...", "msg", flip=True)

		scale_images = False
		image_list = range(1, 10) if not self.debug_mode else [1]
		for i in image_list:
			self.ui_request()
			image_key = "wally_0{0}".format(i)
			#  there are 3 sizes of image included by default; if none match the screen res, choose 1080p then scale
			image_f = os.path.join(Params.image_dir, image_key,"{0}x{1}.jpg".format(*Params.screen_x_y))
			with open(os.path.join(Params.image_dir, image_key, "average_color.txt")) as color_f:
				avg_color = eval(color_f.read())
			if not os.path.isfile(image_f):
				#image_f = os.path.join(Params.image_dir, image_key, "1920x1080.jpg")
				image_f = os.path.join(Params.image_dir, image_key, "1920x1200.jpg")
				scale_images = True
			img_ns = ns(image_f)

			self.backgrounds[image_key] = ([image_key, img_ns, avg_color])
			if scale_images:
				self.backgrounds[image_key][1].scale(Params.screen_x_y)
			self.backgrounds[image_key][1] = self.backgrounds[image_key][1].render()

	def block(self):
		pass

	def setup_response_collector(self):
		pass

	def trial_prep(self):
		self.angle = int(self.angle)
		self.n_back = int(self.n_back)
		self.saccade_count = randrange(self.min_saccades, self.max_saccades)
		self.fill()
		m = self.message("Generating targets...", blit=False)
		self.blit(m)
		self.flip()
		errors = 0
		while len(self.locations) != self.saccade_count:
			self.fill()
			self.blit(m, location=(25,25))
			try:
				self.generate_locations()
			except (TrialException, ValueError):
				errors += 1
				self.message("Failed attempts: {0}".format(errors), location=(25,50))
				self.locations = []
			self.flip()

		self.bg = self.backgrounds[self.bg_image]
		Params.clock.register_event(ET("initial fixation end", Params.fixation_interval))
		self.eyelink.drift_correct(boundary="trial_fixation")
		self.display_refresh(True)

	def trial(self):
		self.eyelink.start(Params.trial_number)
		self.initial_fixation()
		show_dc_target = True
		for l in self.locations:
			# assert a previous location if there is one for reference later in the loop
			if l.index > 0:
				l_prev = self.locations[l.index - 1]
				l.onset_delay(l_prev)  # does nothing when Params.inter_disc_interval is False
			else:
				l_prev = None # ie. first location

			self.display_refresh(show_dc_target, [l, l_prev]) # get this done right away for initial blit
			while self.evi.before(l.event_timeout_label, True): # l.timed_out is True by default, must be written to False
				if l.index == 0:
					show_dc_target = not l.initial_blit
				# show previous disc if it's not yet been left and Params.persist_to_exit_saccade == True
				l.boundary_check()
				if l_prev:
					l_prev.check_persistence()  # if check sets state=False, display_refresh() will set off_timestamp
				if l.rt > 0:  # -1 by default
					break
				self.display_refresh(show_dc_target, [l, l_prev])
				self.ui_request()
			if l.timed_out is None:  # ie. should be False by now
				l.timed_out = True

		self.eyelink.stop()
		return {"trial_num": Params.trial_number,
				"block_num": Params.block_number,
				"bg_image": self.bg[0],
				"timed_out": self.locations[-1].timed_out,
				"rt": self.locations[-1].rt,
				"target_type": "NBACK" if self.locations[-1].n_back else "NOVEL",
				"bg_state": self.bg_state,
				"n_back": self.n_back,
				"amplitude": px_to_deg(self.locations[-1].amplitude),
				"real_angle": int(self.locations[-1].angle + self.locations[-1].rotation),
				"deviation": self.angle if self.angle <= 180 else self.angle - 180,
				"saccades": self.saccade_count}

	def trial_clean_up(self):
		if Params.trial_id:  # ie. if this isn't a recycled trial
			for l in self.locations:
				self.database.insert( {
				'participant_id': Params.participant_id,
				'trial_id': Params.trial_id,
				'trial_num': Params.trial_number,
				'block_num': Params.block_number,
				'location_num': l.index,
				'x': l.x_y_pos[0],
				'y': l.x_y_pos[1],
				'amplitude': l.amplitude,
				'angle': l.angle,
				'n_back': l.n_back,
				'penultimate': l.penultimate,
				'final': l.final,
				'timed_out': l.timed_out,
				'rt': -1 if not l.rt else l.rt,
				'fixate_trial_time': l.fixation[0],
				'fixate_el_time': l.fixation[1],
				},'trial_locations', False)
		self.locations = []
		self.eyelink.clear_boundaries(["trial_fixation"])
		self.bg = None

	def clean_up(self):
		pass

	def initial_fixation(self):
		self.display_refresh(True)
		while self.evi.before("initial fixation end", True):
			if self.eyelink.saccade_from_boundary("trial_fixation"):
				fif_e = ET("failed initial fixation", Params.clock.trial_time + 1.0, None, False, TK_S)
				Params.clock.register_event(fif_e)
				while self.evi.before("failed initial fixation", True):
					self.fill(RED)
					self.blit(self.looked_away_msg, BL_CENTER, Params.screen_c)
					self.flip()
				raise TrialException("Gaze out of bounds.")
		self.display_refresh(True)

	def display_refresh(self, drift_correct=False, discs=[]):
		#  handle the removal of background image on absent condition trials
		self.ui_request()
		if self.bg_state != BG_ABSENT:
			try:
				final = discs[0].final
			except IndexError:
				final = False
			if final and self.bg_state == BG_INTERMITTENT:
				self.fill(self.bg[2])
			else:
				self.blit(self.bg[1])
		else:
			self.fill(GREY)

		#  show the drift correct target if need be
		if drift_correct:
			self.blit(kld.drift_correct_target(), position=Params.screen_c, registration=5)

		#  blit passed discs if they're allow_blit attribute is set
		for d in discs:
			if d is not None:
				d.blit()  # disc manages whether this function executes or not based on it's state attribute

		self.flip()

		#  log timestamps for discs turning on or off
		for d in discs:
			if d is not None:
				timestamp = [Params.clock.trial_time, self.eyelink.now()]
				if d.allow_blit:
					if not d.on_timestamp:
						d.record_start(timestamp)
				elif not d.off_timestamp and d.initial_blit:
					d.off_timestamp = timestamp

	def generate_locations(self):
		self.n_back_index = self.saccade_count - (2 + self.n_back)  # 1 for index, 1 b/c  n_back counts from penultimate saccade
		failed_generations = 0

		# generate locations until there are enough for the trial
		while len(self.locations) < self.saccade_count:
			self.ui_request()
			try:
				self.locations.append(DiscLocation(self))
			except TrialException:
				failed_generations += 1
				if failed_generations > 10:
					raise
				self.generate_locations()


class DiscLocation(object):

	def __init__(self, exp):
		self.errors = 0
		self.exp = exp
		try:
			self.origin = self.exp.locations[-1].x_y_pos
		except IndexError:
			self.origin = Params.screen_c
		self.initial_blit = False
		self.amplitude = None
		self.angle = None
		self.rotation = 0
		self.index = len(self.exp.locations)
		self.boundary = "saccade_{0}".format(self.index)
		self.boundary_img = None
		self.x_y_pos = (None, None)
		self.x_range = range(self.exp.display_margin, Params.screen_x - self.exp.display_margin)
		self.y_range = range(self.exp.display_margin, Params.screen_y - self.exp.display_margin)
		self.viable = True
		self.exp.search_disc_proto.fill = self.exp.search_disc_color
		self.persists = Params.persist_to_exit_saccade
		self.timeout_interval = Params.disc_timeout_interval
		self.penultimate = self.index == self.exp.saccade_count - 2
		self.n_back = self.index == self.exp.n_back_index

		# next attributes are for use during trial
		self.__exit_time = None
		self.on_timestamp = None
		self.off_timestamp = None
		self.timeout_at = None  # records the onset time of the timeout event, to be updated after first blit
		self.__timed_out = None  # only set to false once fixated
		self.previous_disc = None  # only set in trials when Params.inter_disc_interval is not False
		self.fixation = [-1.0, -1.0]  # will be Params.clock.trial_time & eyelink.now() if fixated before timeout
		self.rt = -1.0  # only the final location will populate this value
		self.final = self.index == self.exp.saccade_count - 1
		self.allow_blit = True
		self.idi = Params.inter_disc_interval  # shorthand for coding
		if self.idi and self.index == 0:
			self.idi = 0  # no onset delay for first disc
			self.allow_blit = True

		if self.final:
			self.timeout_interval = Params.final_disc_timeout_interval

		while self.angle is None:
			self.exp.ui_request()
			try:
				self.__generate_location__()
			except TrialException:
				self.errors += 1
				if self.errors > 10:
					raise
		self.disc = self.exp.search_disc_proto.render()
		self.name = "L_{0}_{1}x{2}".format(self.index, self.x_y_pos[0], self.x_y_pos[1])
		self.event_start_label = self.name + "_start"
		self.event_timeout_label = self.name + "_timeout"
		self.event_fixate_label = self.name + "_fixate"
		self.event_exit_label = self.name + "_exit"
		self.onset_delay_label = self.name + "_onset_delay_disc"

	def __str__(self):
		f = "F" if self.final else "-"
		p = "P"if self.penultimate else "-"
		n = "N"if self.n_back else "-"
		str_vars = list(self.x_y_pos) + list(self.origin)
		str_vars.extend([self.amplitude, self.angle, hex(id(self)), self.index, f, p, n])
		return "<DiscLocation {7}{8}{9}{10} ({0},{1}) from ({2},{3}) ({4}px along {5} deg) at {6}>".format(*str_vars)

	def __generate_location__(self):
		if self.final:
			n_back = self.exp.locations[self.exp.n_back_index]
			penultimate = self.exp.locations[-1]
			angle = self.exp.angle
			amplitude = int(line_segment_len(n_back.x_y_pos, penultimate.x_y_pos))
			self.rotation = angle_between(penultimate.x_y_pos, n_back.x_y_pos)
		else:
			amplitude = randrange(self.exp.min_amplitude, self.exp.max_amplitude)
			angle = randrange(0, 360)
		self.x_y_pos = point_pos(self.origin, amplitude, angle, self.rotation)
		# ensure disc is inside drawable bounds; if penultimate saccade, ensure all final saccade angles are possible
		self.__margin_check()
		self.__penultimate_viability_check__()

		# assign generation output
		self.angle = angle
		self.amplitude = amplitude
		self.__add_eyelink_boundary__()

	def __margin_check(self, p=None, penultimate=False):
		if not p: p = self.x_y_pos
		m = self.exp.display_margin
		if not (m < p[0] < Params.screen_x - m and m < p[1] < Params.screen_y - m):
			raise TrialException("{0}ocation inviable.".format("(P)l" if penultimate else "L"))

	def __penultimate_viability_check__(self):
		if not self.penultimate:
			return
		d_xy = line_segment_len(self.x_y_pos, self.exp.locations[self.exp.n_back_index].x_y_pos)
		disc_diam = self.exp.search_disc_proto.surface_width
		if d_xy - disc_diam < disc_diam:
			raise ValueError("Penultimate target too close to n-back target.")
		theta = angle_between(self.x_y_pos, self.exp.locations[self.exp.n_back_index].x_y_pos)
		for a in range(0, 360, 60):
			self.__margin_check(point_pos(self.x_y_pos, d_xy, a + theta))
		self.exp.search_disc_proto.fill = BLACK
		self.penultimate = True

	def __add_eyelink_boundary__(self):
		d = int(self.exp.search_disc_proto.surface_width + self.exp.disc_boundary_tolerance)
		self.boundary_img = kld.Circle(d, [1, (255,0,0,125)]).render()
		try:
			self.exp.eyelink.add_boundary("saccade_{0}".format(self.index), [self.x_y_pos, d], CIRCLE_BOUNDARY)
		except AttributeError:
			self.exp.add_boundary("saccade_{0}".format(self.index), [self.x_y_pos, d], CIRCLE_BOUNDARY)

	def blit(self):
		# for all possible conditions, timed-out discs are removed
		if self.timed_out:
			return
		if self.allow_blit:
			self.exp.blit(self.disc, 5, self.x_y_pos)
			self.initial_blit = True

	def boundary_check(self):
		if not self.initial_blit:
			return
		if self.final:
			check_time = self.exp.eyelink.saccade_to_boundary(self.boundary, EL_SACCADE_END)
			if check_time:
				self.exp.fill()
				self.exp.flip()
		else:
			check_time = self.exp.eyelink.fixated_boundary(self.boundary, EL_FIXATION_END)
			#print "check_time: " + str(check_time) + " [" + str(self.exp.eyelink.now()) + "]"
		if check_time:
			self.timed_out = False
			timestamp = [Params.clock.trial_time, check_time]
			if self.final:
				self.rt = timestamp[0] - self.on_timestamp[0]
				return
			self.record_fixation(timestamp)
			self.exp.eyelink.clear_queue()
			return True

	def check_persistence(self):
		# not applicable on immediate-behavior targets
		if self.persists is False or self.timed_out is True:
			return
		#  only called when disc is assigned to l_prev in trial()
		if self.exit_time is None:
			self.record_exit()


	def onset_delay(self, previous_disc):
		# not applicable on persistent-behavior targets
		if self.persists:
			return
		self.previous_disc = previous_disc
		if self.previous_disc.timed_out:
			return
		try:
			Params.clock.register_event(ET(self.onset_delay_label, self.idi, relative=True))
		except TypeError:  # ie. inter_disc_interval was False
			pass
		while self.exp.evi.before(self.onset_delay_label, True):
			pass
		self.previous_disc.allow_blit = False

	def record_fixation(self, timestamp):
		self.exp.evi.write(self.event_fixate_label + " (trial_time={0})".format(timestamp[0]))
		self.fixation = timestamp
		self.rt = timestamp[0] - self.on_timestamp[0]  # use eye_link time for for RT

	def record_exit(self):
		if self.exp.eyelink.within_boundary(self.boundary, EL_GAZE_POS):
			return False
		else:
			self.exit_time = [Params.clock.trial_time, self.exp.eyelink.now()]
			# off_timestamp recorded separately (and externally in display_refresh()) on next call flip()
			self.exp.evi.write(self.event_exit_label + "(trial_time={0})".format(self.exit_time[0]))
			return True

	def record_start(self, timestamp):
		# eye-link time unnecessary as the eyelink will supply this in the EDF when written
		self.exp.evi.write(self.event_start_label + " (trial_time={0})".format(timestamp[0]))
		self.on_timestamp = timestamp
		Params.clock.register_event(ET(self.event_timeout_label, self.timeout_interval, relative=True))

	@property
	def exit_time(self):
		return self.__exit_time

	@exit_time.setter
	def exit_time(self, t):
		if t:
			self.allow_blit = False
			self.__exit_time = t
		else:
			self.__exit_time = None

	@property
	def timed_out(self):
		return self.__timed_out

	@timed_out.setter
	def timed_out(self, state):
		self.__timed_out = state
		if state:
			self.allow_blit = False