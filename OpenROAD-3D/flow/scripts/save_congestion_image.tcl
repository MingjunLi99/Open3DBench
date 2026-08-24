gui::save_display_controls

set height [[[ord::get_db_block] getBBox] getDY]
set height [ord::dbu_to_microns $height]
set resolution [expr $height / 1000]

gui::clear_selections
gui::set_display_controls "*" visible false
gui::set_display_controls "Heat Maps/Routing Congestion" visible true
save_image -resolution $resolution $::env(CONGESTION_IMAGE_FILE)

gui::restore_display_controls
