
#  /etc/rc.d/functions.d/fbsplash-extras.sh                                  #

#  Improved Fbsplash script for Chakra GNU/Linux initscripts                 #
#                                                                            #
#  Author:                Kurt J. Bosch    <kjb-temp-2009 at alpenjodel.de>  #
#  Based on the work of:  Greg Helton                <gt at fallendusk.org>  #
#                         Thomas Baechler         <thomas at archlinux.org>  #
#                         Michal Januszewski          <spock at gentoo.org>  #
#                         and others                                         #
#                                                                            #
#  Distributed under the terms of the GNU General Public License (GPL)       #

## Utility functions

# Get a (rough) list of 'services' to start/stop from given initscript
# for triggering splash progress and events
#
splash_initscript_svcs_get() {        # args: <initscript> [list]
	local fd line msg svc
	exec {fd}<"$1" || return
	while read -u $fd line ; do
		[[ $line =~ (^|[[:space:]])(stat_busy|status)[[:space:]]+(\"([^\"]+)\")? ]] || continue
		msg=${BASH_REMATCH[4]}
		# Sort out skipped
		case $msg
		in *SIGTERM* | *SIGKILL* ) continue ## http://bugs.archlinux.org/task/10536 ## FIXME ##
		esac
		# Print full list
		if [[ ${2} = list ]]; then
			echo $( splash_msg_to_svc "$msg" ) "$msg"
			continue
		fi
		# Try to sort out inactive
		case $msg
		in "Loading Modules"     ) ! [[ $load_modules = off ]]
		;; *RAID*                ) splash_test_file -r /etc/mdadm.conf 'ARRAY.*'
		;; *LVM*                 ) [[ $USELVM = yes || $USELVM = YES ]]
		;; *"encrypted volumes"* ) splash_test_file -r /etc/crypttab
		;; "Setting Hostname"*   ) [[ $HOSTNAME ]]
		;; "Setting NIS Domain Name"* )
			(	[ -r /etc/conf.d/nisdomainname ] && . /etc/conf.d/nisdomainname
				[[ $NISDOMAINNAME ]] )
		;; "Loading Keyboard Map"* ) [[ $KEYMAP ]]
		;; "Setting Consoles to UTF-8 mode"  ) [[ ${LOCALE,,*} == *utf* ]]
		;; "Setting Consoles to legacy mode" ) ! [[ ${LOCALE,,*} == *utf* ]]
		;; "Adding persistent cdrom udev rules" )
			[ -f /dev/.udev/tmp-rules--70-persistent-cd.rules ]
		;; "Adding persistent network udev rules" )
			[ -f /dev/.udev/tmp-rules--70-persistent-net.rules ]
		esac || continue
		# echo a service name
		splash_msg_to_svc "$msg"
	done
	exec {fd}<&-
}

# Test a file and check if it contains any significant lines
#
splash_test_file() {            # args: <test-operator> <file> [<regex>]
	local regex=${3:-'[[:space:]]*[^#[:space:]].*'}
	test ${1} "${2}" && [[ $( <"${2}" ) =~ (^|$'\n')${regex}($'\n'|$) ]]
}

# Generate a 'service' name from a initscript stat_busy message text
#
splash_msg_to_svc() {           # args: <message>
	local msg=${1}
	msg=${msg,,*}    # make lowercase
	msg=${msg%%:*}   # remove variables part
	local svc
	# Try to get an action and object
	if [[ $msg =~ ^(de|un)?(([a-z]+)ing )?((for|up|down|on|off) )?((.{4,}) to .*|(.{4,}))$ ]]
	then
		local action=${BASH_REMATCH[3]}
		local object=${BASH_REMATCH[7]}${BASH_REMATCH[8]}
		# Drop most of the actions to get good start/stop matching
		case $action
		in (activat|add|bring|configur|initializ|load|lock|remov|sav|sett|start|stop)
			svc=$object
		;; (*)
			svc="$action $object"
		esac
	else
		svc=${msg}
	fi
	# Convert whitespace
	svc=${svc//[ $'\t']/_}
	# Fix remaining non-matches
	case $svc
	in   mount_filesystems ) svc=mount_local_filesystems
	esac
	# Use some 'namespace' to allow distinguishing from daemons
	echo _init_$svc
}

## Actual splash code

case $PREVLEVEL:$RUNLEVEL
in N:[S2-5]   ) : # bootup
;; [2-5]:S    ) : # go single
;; S:[2-5]    ) : # re-enter multi
;; [2-5]:[06] ) : # shutdown
;; * ) return     # do nothing
esac

# Only do this where needed
# Since we use BASH, all important functions and variables are exported
case ${0#/etc/rc.} in sysinit | multi | single | shutdown )
	# splash-functions.sh will run splash_setup which needs /proc
	if ! /bin/mountpoint -q /proc; then
	  /bin/mount -n -t proc none /proc
	fi
	export SPLASH_PUSH_MESSAGES="no"
	export SPLASH_VERBOSE_ON_ERRORS="no"
	. /sbin/splash-functions.sh # /etc/conf.d/splash is also sourced by this
	unset options opt i # eliminate splash_setup non local vars    ## FIXME ##
	export SPLASH_MESSAGE=$SPLASH_BOOT_MESSAGE
	export SPLASH_TYPE="bootup"
	declare -ix SPLASH_STEPS=0
	declare -ix SPLASH_STEPS_DONE=0
	declare -A SPLASH_STEPS_SYSINIT=()
esac

# Verbose mode is handled by fbcondecor kernel patch and daemon script
[[ $SPLASH_MODE_REQ = silent ]] || return 0

# splash-functions override - Don't try to use /usr/bin/basename
splash_comm_send() {
	[[ -r $spl_pidfile && $( /bin/pidof -o %PPID $spl_daemon ) = $( <$spl_pidfile ) ]] || return 1
	splash_profile comm "$@"
	echo "$@" >$spl_fifo &
}

# splash-functions override - Always write debug log, regardless of SPLASH_PROFILE
splash_profile() {
	local time rest; read time rest </proc/uptime
	echo "$time: $*" >>$spl_cachedir/profile
}

splash_msg() {
	splash_profile "info" "$@"
	echo "splash:" "$@"
}

# Count bootup progress steps
# Write list file for 'splash_svclist_get start'
splash_svc_init_bootup() {
	# rc.sysinit 'services'
	SPLASH_STEPS=0
	local svc
	for svc in $( splash_initscript_svcs_get /etc/rc.sysinit ); do
		[[ ${SPLASH_STEPS_SYSINIT[$svc]} ]] && continue # skip missed and dupes
		SPLASH_STEPS_SYSINIT[$svc]=$((++SPLASH_STEPS))
		echo $svc
	done >|$spl_cachedir/svcs_start
	echo $SPLASH_STEPS >|$spl_cachedir/steps_sysinit
	# rc.multi services
	SPLASH_STEPS+=1 # rc.local
	local daemon
	for daemon in "${DAEMONS[@]}"; do
		case $daemon
		in $SPLASH_XSERVICE | @$SPLASH_XSERVICE )
			SPLASH_STEPS+=-1 # revert rc.local
			break
		;; \!* ) continue
		;; \@* ) :
		;;   * ) SPLASH_STEPS+=1
		esac
		echo ${daemon#@}
	done >>$spl_cachedir/svcs_start
	echo $SPLASH_STEPS >|$spl_cachedir/steps_bootup
}

# Write list file for 'splash_svclist_get stop'
splash_svc_init_shutdown() {
	# 'daemons'
	/bin/ls -1t /var/run/daemons >>$spl_cachedir/svcs_stop
	# rc.shutdown 'services'
	splash_initscript_svcs_get /etc/rc.shutdown >>$spl_cachedir/svcs_stop
}

# Trigger a service event
splash_svc_event() {
	local svc=$1
	if [[ $SPLASH_START_PENDING ]]; then # missing the step
		SPLASH_STEPS_SYSINIT[$svc]=0
		return
	fi
	local event=$2
	splash_run_hook pre  svc_"$event" "$svc"
	splash_comm_send update_svc "$svc" svc_"$event"
	splash_run_hook post svc_"$event" "$svc"
	splash_comm_send paint
}

# Run theme hook script if any
splash_run_hook() {             # args: 'pre'|'post' <event> [arg]...
	local hook_script=/etc/splash/$SPLASH_THEME/scripts/${2}-${1}
	if [[ -x $hook_script ]]; then
		splash_profile "$@"
		shift 2
		"$hook_script" "$@"
	fi
}

# Hook into initscripts, but don't do anything without a tmpfs!
case $0
in   /etc/rc.sysinit )
	if [[ -p /dev/.splash-cache/${spl_fifo##*/} ]]; then
		/bin/mount --bind /dev/.splash-cache $spl_cachedir || return 0
		# Continue to use a splash daamon started in initcpio
		splash_profile "note Using initcpio daemon"
		splash_comm_send set message "$SPLASH_BOOT_MESSAGE"
		splash_svc_init_bootup
		# *no* pre hook script should exist in this case!
		splash_run_hook post rc_init sysinit $RUNLEVEL
	else
		# Mount a new tmpfs
		( splash_cache_prep ) || return 0
		# Paint the initial splash if not done in initcpio
		if ! [[ $( $spl_bindir/fgconsole ) = $SPLASH_TTY ||
				$( /bin/pidof -o %PPID fbcondecor_helper ) ]]; then
			splash_profile fbcondecor_helper init
			BOOT_MSG=$SPLASH_BOOT_MESSAGE \
				/sbin/fbcondecor_helper 2 init $SPLASH_TTY 0 $SPLASH_THEME
		fi
		splash_profile "note Will use deferred daemon start"
		SPLASH_START_PENDING=1
	fi
	# The infamous Prevent_Splash_Destruction_Magic (tm)
	SPLASH_CONSOLEFONT=$CONSOLEFONT
	CONSOLEFONT=""
	add_hook sysinit_udevlaunched splash_sysinit_udevlaunched
	add_hook sysinit_udevsettled  splash_sysinit_udevsettled
	add_hook sysinit_prefsck      splash_sysinit_prefsck
	add_hook sysinit_postfsck     splash_sysinit_postfsck
	add_hook sysinit_prefsckloop  splash_sysinit_prefsck
	add_hook sysinit_postfsckloop splash_sysinit_postfsck
	add_hook sysinit_end          splash_sysinit_end
	splash_sysinit_udevlaunched() {
		[[ $SPLASH_START_PENDING ]] || return 0
		# Deferre if helper still doing fadein
		if [[ $( /bin/pidof -o %PPID fbcondecor_helper ) ]]; then
			return
		fi
		stat_busy "Preparing for Fbsplash daemon start"
		splash_profile prepare_start_udevlaunched
		if [[ $( /bin/pidof -o %PPID /sbin/udevd ) ]]; then
			/sbin/udevadm control --property=STARTUP=1
			/sbin/udevadm trigger --action=add --subsystem-match={tty,graphics,input}
		fi
		splash_svc_init_bootup
		splash_run_hook pre  rc_init sysinit $RUNLEVEL
		if [[ $( /bin/pidof -o %PPID /sbin/udevd ) ]]; then
			/sbin/udevadm settle
		fi
		local t=$(( $( /bin/date +%s%N ) - t0 )); t=$((t/1000000))
		stat_append "($((t/1000)).$((t%1000))s)"
		stat_done
		# Start splash
		splash_start
		unset SPLASH_START_PENDING
		splash_run_hook post rc_init sysinit $RUNLEVEL
	}
	splash_sysinit_udevsettled() {
		[[ $SPLASH_START_PENDING ]] || return 0
		stat_busy "Preparing for Fbsplash daemon start"
		splash_profile prepare_start_udevsettled
		splash_svc_init_bootup
		splash_run_hook pre  rc_init sysinit $RUNLEVEL
		if [[ $( /bin/pidof -o %PPID fbcondecor_helper ) ]]; then
			stat_append "(fadein-wait)"
			splash_profile splash_wait fbcondecor_helper
			splash_wait fbcondecor_helper
			if [ $? -ne 0 ]; then
				stat_fail
				splash_msg "Broken framebuffer driver?"
				return
			fi
			stat_done
		fi
		# Start splash
		splash_start
		unset SPLASH_START_PENDING
		splash_run_hook post rc_init sysinit $RUNLEVEL
	}
	splash_sysinit_prefsck() {
		if [[ $SPLASH_AUTOVERBOSE = 0 ]]; then
			stat_append " (progress forwarded to Fbsplash)"
			echo # newline!
			splash_fsck_forward_d
		fi
	}
	splash_sysinit_postfsck() {
		if [[ $FSCK_FD ]]; then
			exec {FSCK_FD}>&-
			unset FSCK_FD
		fi
		# fsck failure emergency exit
		if [ ${fsckret} -gt 1 -a ${fsckret} -ne 32 ]; then
			splash_verbose # chvt
		fi
	}
	splash_sysinit_end() {
		read SPLASH_STEPS_DONE <$spl_cachedir/steps_sysinit
		splash_update_progress
		splash_run_hook pre  rc_exit $RUNLEVEL
		splash_run_hook post rc_exit $RUNLEVEL
		if [[ " "$( </proc/cmdline )" " =~ " "(s|S|single|1)" " ]]; then
			splash_verbose # chvt
			CONSOLEFONT=$SPLASH_CONSOLEFONT set_consolefont
		fi
	}
;;   /etc/rc.multi )
	/bin/mountpoint -q $spl_cachedir || return 0
	if [[ $PREVLEVEL = N ]]; then
		read SPLASH_STEPS_DONE <$spl_cachedir/steps_sysinit
		read SPLASH_STEPS <$spl_cachedir/steps_bootup
		splash_run_hook pre  rc_init boot $RUNLEVEL
		if [[ " "$( </proc/cmdline )" " =~ " "(s|S|single|1)" " ]]; then
			splash_comm_send set mode silent # chvt
		fi
		splash_run_hook post rc_init boot $RUNLEVEL
	fi
	add_hook multi_end   splash_multi_end
	start_daemon() {
		if [[ $1 = $SPLASH_XSERVICE ]]; then
			SPLASH_EXIT_TYPE=staysilent splash_end
		fi
		splash_start_daemon $1
		SPLASH_STEPS_DONE+=1
		splash_update_progress
	}
	start_daemon_bkgd() {
		if [[ $1 = $SPLASH_XSERVICE ]]; then
			SPLASH_EXIT_TYPE=staysilent splash_end
		fi
		stat_bkgd "Starting $1"
		( SPLASH_PUSH_MESSAGES="no" splash_start_daemon $1 ) &>/dev/null &
	}
	splash_start_daemon() {
		splash_svc_event $1 start
		/etc/rc.d/$1 start
		if [[ $1 = gpm ]]; then
			splash_comm_send set gpm; splash_comm_send repaint
		fi
		local event=started; [[ -e $spl_cachedir/start_failed-$1 ]] && event=start_failed
		splash_svc_event $1 $event
	}
	splash_multi_end() {
		# Always stop/paint/fadeout before X does chvt (black screen)
		if ! in_array "$SPLASH_XSERVICE" "${DAEMONS[@]}"; then
			if [[ $RUNLEVEL = 5 ]]; then
				SPLASH_EXIT_TYPE=staysilent splash_end
			else
				splash_end
			fi
		fi
		# Umount the tmpfs copying some debug info to the disk
		splash_cache_cleanup profile svcs_start steps_sysinit steps_bootup
	}
	splash_end() {
		if [[ $PREVLEVEL = N ]]; then
			# Stop splash
			splash_run_hook pre  rc_exit $RUNLEVEL
			splash_exit
			splash_run_hook post rc_exit $RUNLEVEL
			# The infamous blah-blah...
			if ! [[ " "$( </proc/cmdline )" " =~ " "(s|S|single|1)" " ]]; then
				set_consolefont
			fi
		fi
		# Prevent X from doing a chvt back to uggly console on exit
		if [[ $SPLASH_EXIT_TYPE = staysilent &&
		      $( $spl_bindir/fgconsole ) != $SPLASH_TTY ]]; then
			splash_msg "Switching to splash tty for starting X"; chvt $SPLASH_TTY
		fi
	}
;;   /etc/rc.single )
	if [[ $PREVLEVEL = N ]]; then
		return
	fi
	( splash_cache_prep ) || return 0
	# Just override X exit chvt to avoid black screen
	if ck_daemon $SPLASH_XSERVICE; then # *no* 'daemon' to stop
		if [[ $( /bin/pidof -o %PPID /usr/bin/Xorg ) ]]
		then add_hook single_postkillall splash_single_start
		else add_hook single_start       splash_single_start
		fi
	fi
	splash_single_start() {
		splash_wait /usr/bin/Xorg
		splash_verbose # chvt
	}
	stop_daemon() {
		/etc/rc.d/$1 stop
		if [[ $1 = $SPLASH_XSERVICE ]]; then
			splash_single_start
		fi
	}
;; /etc/rc.shutdown )
	( splash_cache_prep ) || return 0
	SPLASH_TYPE=shutdown; SPLASH_MESSAGE=$SPLASH_SHUTDOWN_MESSAGE
	if [[ $RUNLEVEL = 6 ]]; then
		SPLASH_TYPE=reboot; SPLASH_MESSAGE=$SPLASH_REBOOT_MESSAGE
	fi
	# Time based progress - Two seconds intervall to avoid sigkill race
	SPLASH_SLEEP_STEPS=$(( (5+1)/2 ))          # (sigterm_sleep+sigkill_sleep)/2
	SPLASH_STEPS=$(( SPLASH_SLEEP_STEPS + 2 )) # one for daemons, one for the rest
	SPLASH_STEPS_DONE=0
	SPLASH_EXIT_TYPE=staysilent
	# Init for splash start
	splash_svc_init_shutdown
	splash_run_hook pre  rc_init shutdown $RUNLEVEL
	# Not using XSERVICE here to avoid missing errors - X should chvt back to SPLASH_TTY
	add_hook shutdown_start       splash_shutdown_start
	add_hook shutdown_prekillall  splash_shutdown_prekillall
	add_hook shutdown_postkillall splash_restart                   ## FIXME ##
	add_hook shutdown_poweroff    splash_shutdown_poweroff
	splash_shutdown_start() {
		# Override X exit chvt to avoid loosing fadein
		if ck_daemon  $SPLASH_XSERVICE; then # *no* 'daemon' to stop
			splash_wait /usr/bin/Xorg
			if [[ ,$SPLASH_EFFECTS, == *,fadein,* &&
			      $( $spl_bindir/fgconsole ) = $SPLASH_TTY ]]; then
				splash_msg "Switching away from splash tty to enable fadein"; chvt 63
			fi
		fi
		# Start splash
		splash_start
		splash_run_hook post rc_init shutdown $RUNLEVEL
		# Prevent gpm from garbling the splash
		if ! ck_daemon gpm; then
			splash_comm_send set gpm; splash_comm_send repaint
		fi
	}
	stop_daemon() {
		splash_svc_event $1 stop
		/etc/rc.d/$1 stop
		local event=stopped; [[ -e $spl_cachedir/stop_failed-$1 ]] && event=stop_failed
		splash_svc_event $1 $event
	}
	splash_shutdown_prekillall() {
		SPLASH_STEPS_DONE+=1
		splash_update_progress # for stopping 'daemons'
		(
			trap : SIGTERM                                         ## FIXME ##
			restarted=""                                                    ##
			for (( i=0; i<SPLASH_SLEEP_STEPS; i++ )) do
				if [[ ! $( /bin/pidof -o %PPID $spl_daemon ) && ! $restarted ]] ##
				then                                                            ##
					splash_restart                                              ##
					restarted=1                                                 ##
				fi                                                     ## FIXME ##
				/bin/sleep 2
				SPLASH_STEPS_DONE+=1
				splash_update_progress
			done
		) &
		SPLASH_STEPS_DONE+=$SPLASH_SLEEP_STEPS
	}
	## http://bugs.archlinux.org/task/10536                        ## FIXME ##
	splash_restart() {
		[[ $( $spl_bindir/fgconsole ) = $SPLASH_TTY ]] || return 0
		if [[ $SPLASH_PUSH_MESSAGES = yes ]]; then
			SPLASH_MESSAGE=$SPLASH_BUSY_MSG
		fi
		SPLASH_RESTART=1 splash_run_hook pre  rc_init shutdown $RUNLEVEL
		PROGRESS=$(( 65535*SPLASH_STEPS_DONE/SPLASH_STEPS )) \
			splash_start
		SPLASH_RESTART=1 splash_run_hook post rc_init shutdown $RUNLEVEL
		local svc_event_file
		for svc_event_file in $spl_cachedir/stop_failed-*; do
			[[ -f $svc_event_file ]] || continue
			splash_svc_event ${svc_event_file##*/stop_failed-} stop_failed
		done
		if [[ -e $spl_cachedir/msg_log ]]; then
			local line
			while read line; do
				splash_comm_send log "$line"
			done <$spl_cachedir/msg_log
		fi
		splash_comm_send repaint
	}
	##
	splash_shutdown_poweroff() {
		# Finish the splash
		splash_run_hook pre  rc_exit $RUNLEVEL
		splash_exit
		splash_run_hook post rc_exit $RUNLEVEL
	}
;; * )
	/bin/mountpoint -q $spl_cachedir || return 0
esac

# splash-functions override - Do something usefull
splash_update_progress() {
	if [[ $SPLASH_STEPS -gt 0 ]]; then
		splash_comm_send progress $(( 65535*SPLASH_STEPS_DONE/SPLASH_STEPS ))
		splash_comm_send paint
	fi
}

# splash-functions override - Don't chvt if not on splash, explain what's going on
splash_verbose() {
	if [[ $( $spl_bindir/fgconsole ) = $SPLASH_TTY ]]; then
		splash_msg "Switching to console"; chvt 1
	fi
}

# splash-functions override - No keyboard grab, verbose mode, CONSOLE parameter
splash_start() {
	SPLASH_PUSH_MESSAGES="no" \
		stat_busy "Starting Fbsplash daemon"
	splash_profile splash_start
	local options=()
	[[ $SPLASH_EFFECTS       ]] && options+=( --effects=$SPLASH_EFFECTS )
	[[ $SPLASH_TEXTBOX = yes ]] && options+=( --textbox )
	[[ $SPLASH_THEME         ]] && options+=( --theme=$SPLASH_THEME )
	/bin/rm -f $spl_pidfile
	local retval=1
	if [[ $console = tty1 || $SPLASH_SANITY = insane ]]; then
		BOOT_MSG=$SPLASH_MESSAGE \
			"$spl_daemon" --pidfile=$spl_pidfile --type=$SPLASH_TYPE "${options[@]}"
		retval=$?
	else
		splash_msg "Fbsplash requires console=tty1 in kernel line!"
	fi
	if [ $retval -eq 0 ]; then
		splash_comm_send set tty silent $SPLASH_TTY
		splash_comm_send set mode silent
		splash_comm_send repaint
		splash_comm_send set autoverbose $SPLASH_AUTOVERBOSE
		splash_profile splash_start end
		stat_done
	else
		splash_profile splash_start failed
		stat_fail
	fi
}

# splash-functions override - Finish the splash before stopping the daemon
splash_exit() {
	[[ -f $spl_pidfile ]] || return 0
	splash_profile splash_exit
	# Wipe the last stat_busy message
	if [[ $SPLASH_PUSH_MESSAGES = yes ]]; then
		splash_comm_send set message "$SPLASH_MESSAGE"
		splash_comm_send paint
	fi
	# Set 100% progress
	splash_comm_send progress 65535
	splash_comm_send paint && /bin/sleep .1
	# Keep the daemon for shutdown
	if [[ $RUNLEVEL == [06] && ,$SPLASH_EFFECTS, != *,fadeout,* ]]; then
		return
	fi
	SPLASH_PUSH_MESSAGES="no" \
		stat_busy "Stopping Fbsplash daemon"
	local retval=1
	if [[ $( /bin/pidof -o %PPID $spl_daemon ) ]]; then
		# Fadeout/Stop the daemon
		splash_comm_send exit $SPLASH_EXIT_TYPE
		splash_wait $spl_daemon &&
			/bin/rm -f $spl_pidfile
		retval=$?
	else
		splash_msg "The Fbsplash daemon has already died inexpectedly!"
	fi
	splash_profile splash_exit end
	if [ $retval -eq 0 ]; then
		stat_done
	else
		stat_fail
	fi
}

# Wait until timeout or given binary dies
splash_wait() {
	local -i i=0
	while [[ i++ -lt 100 ]]; do
		[[ $( /bin/pidof -o %PPID "${1}" ) ]] || return 0
		/bin/sleep .1
	done
	splash_msg "Timeout waiting on '$1' to die!"
	return 1
}

# initscripts override
stat_busy() {
	printf "${C_OTHER}${PREFIX_REG} ${C_MAIN}${1}${C_CLEAR} "
	printf "${SAVE_POSITION}"
	deltext
	printf "   ${C_OTHER}[${C_BUSY}BUSY${C_OTHER}]${C_CLEAR} "
	SPLASH_BUSY_MSG=$1
	if [[ $SPLASH_PUSH_MESSAGES = yes ]]; then
		splash_comm_send set message "${1}"
		splash_comm_send paint
	fi
	case $0
	in /etc/rc.sysinit )
		SPLASH_BUSY_SVC=$( splash_msg_to_svc "$SPLASH_BUSY_MSG" )
		splash_svc_event $SPLASH_BUSY_SVC start
	;; /etc/rc.shutdown )
		SPLASH_BUSY_SVC=$( splash_msg_to_svc "$SPLASH_BUSY_MSG" )
		splash_svc_event $SPLASH_BUSY_SVC stop
	esac
}

# initscripts override
stat_done() {
	deltext
	printf "   ${C_OTHER}[${C_DONE}DONE${C_OTHER}]${C_CLEAR} \n"
	case $0
	in /etc/rc.sysinit )
		splash_svc_event $SPLASH_BUSY_SVC started
		splash_sysinit_step
	;; /etc/rc.shutdown )
		splash_svc_event $SPLASH_BUSY_SVC stopped
	esac
}

# initscripts override
stat_fail() {
	deltext
	printf "   ${C_OTHER}[${C_FAIL}FAIL${C_OTHER}]${C_CLEAR} \n"
	local event=stop_failed; [[ $PREVLEVEL = N ]] && event=start_failed
	# Provide a general failure status and write to msglog textbox
	splash_comm_send update_svc fbsplash-dummy svc_${event}
	splash_comm_send log "Error $SPLASH_BUSY_MSG"
	splash_comm_send paint
	## Save for restart                                            ## FIXME ##
	: >|$spl_cachedir/${event}-fbsplash-dummy
	echo "Error $SPLASH_BUSY_MSG" >>$spl_cachedir/msg_log
	##
	if [[ $SPLASH_VERBOSE_ON_ERRORS = yes ]]; then
		splash_verbose # chvt
	fi
	local svc
	case $0
	in /etc/rc.sysinit )
		splash_svc_event $SPLASH_BUSY_SVC start_failed
		splash_sysinit_step
	;; /etc/rc.shutdown )
		splash_svc_event $SPLASH_BUSY_SVC stop_failed
	;; /etc/rc.d/* )
		# Mark 'daemon' service as failed
		: >|$spl_cachedir/${event}-${0##*/}
	esac
}

splash_sysinit_step() {
	local -i step=${SPLASH_STEPS_SYSINIT[$SPLASH_BUSY_SVC]}
	if [[ $step -gt $SPLASH_STEPS_DONE ]]; then
		SPLASH_STEPS_DONE=$step
		splash_update_progress
	fi
}

# Get a file descriptor and start a daemon for pushing progress
# info from 'fsck -C$FSCK_FD' to the splash status message line
splash_fsck_forward_d() {
	[[ -w $spl_fifo && $( /bin/pidof -o %PPID $spl_daemon ) ]] || return
	local fsck_fifo=$spl_cachedir/fsck_fifo
	# drop any old fifo and create a new one
	/bin/rm -f $fsck_fifo
	/bin/mkfifo -m 600 $fsck_fifo || return
	(
		PROGRESS=$(( 65535*SPLASH_STEPS_DONE/SPLASH_STEPS ))
		fifo_pid=
		fs_phase=
		pgr=-1
		while :; do
			read -t 2 phase step total fs; ret=$?
			if [ $ret -eq 0 ]; then
				if [[ $fs_phase != ${fs}_$phase ]]; then
					fs_phase=${fs}_$phase
				fi
				new_pgr=$(( 100 * step / total ))
				[ $new_pgr -eq $pgr ] && continue
				pgr=$new_pgr
				pgr_msg="[ ${fs}  phase ${phase}  ${pgr}% ]"
				# cancel obsolete message
				[[ $fifo_pid ]] && kill $fifo_pid 2>/dev/null
				echo "set message $SPLASH_BUSY_MSG ${pgr_msg}" >"${spl_fifo}" &
				fifo_pid=$!
			elif ! [ $ret -gt 128 ]; then # not a timeout
				break
			elif [ $pgr -ge 100 ]; then # phase complete
				# reset - for some FS types the fsck progress FD isn't used
				splash_comm_send set message "$SPLASH_BUSY_MSG"
				fs_phase=
				pgr=-1
			fi
		done
		splash_comm_send set message "$SPLASH_MESSAGE"
	) &>/dev/null <$fsck_fifo &
	exec {FSCK_FD}>$fsck_fifo
}

# EOF #
