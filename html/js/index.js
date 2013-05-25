
$(function(){

	rotate_refresh(0, $('#div_loading .icon-refresh'));

	$('#div_zone_buttons').on('click', 'button', update_zone);

	fetch_zone_data();

});

// Implements the handler function called by fetch_zone_data()
populate_zone_data = function() {
	$('#div_zone_buttons *').remove();
	for(var i = 0; i < zone_info.zone_count; i++) {
		// Avoid error on missing zone data blocks
		if(!zone_info.zone[i])
			zone_info.zone[i] = {'name':'', 'status':0};

		if(1 > zone_info.zone[i]['name'].length)
			zone_info.zone[i]['name'] = 'Zone ' + (i + 1);

		$('<button>')
			.attr({
				'type': 'button',
				'data-zone': i,
				'data-status': zone_info.zone[i]['status']
			})
			.addClass('span2 but' + ((1 == zone_info.zone[i]['status'])?' btn-success':''))
			.text(zone_info.zone[i]['name'])
			.appendTo($('#div_zone_buttons'))
	}

	$('#div_zone_buttons').show();

    window.setTimeout('fetch_zone_data();', 1000 * 10);
}

update_zone = function() {
	$('#div_zone_buttons button').attr('disabled', true);

	var zone = $(this).attr('data-zone');
	var new_status = (0 == $(this).attr('data-status'));
	zone.replace(/[^\d]/, '');

	$.post('/update-zone-status', 'zone=' + escape(zone) + '&status=' + (new_status?1:0))
		.done(function(result) {
			if(0 == result.error) {
				$('#div_update_success').show();

				rotate_refresh(0, $('#div_loading .icon-refresh'));
				$('#div_loading').show();
				fetch_zone_data();
			}
			else {
				$('#div_update_failed')
					.find('.message')
						.text(result.desc)
						.end()
					.show();
			}
		})
		.always(function(){
			$('#div_zone_buttons button').attr('disabled', false);
		});

}

