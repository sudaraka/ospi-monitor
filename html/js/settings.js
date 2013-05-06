
$(function(){

	rotate_refresh(0, $('#div_loading .icon-refresh'));

	$('#btn_save_zone_count').click(save_zone_count);

	$('#btn_save_zone_names').click(save_zone_names);

	fetch_zone_data();

});

// Implements the handler function called by fetch_zone_data()
populate_zone_data = function() {
	$('#txt_zone_count').val(zone_info.zone_count);

	$('#div_zone_name_list *').remove();
	for(var i = 0; i < zone_info.zone_count; i++) {
		// Avoid error on missing zone data blocks
		if(!zone_info.zone[i])
			zone_info.zone[i] = {'name':''};

		$('<div>')
			.addClass('input-prepend span3')
			.append(
				$('<div>')
					.addClass('add-on')
					.text('Zone ' + (i + 1))
			)
			.append(
				$('<input>')
					.attr({'type': 'text', 'name': 'zone_name'})
					.addClass('input-small')
					.val(zone_info.zone[i].name)
			)
			.appendTo($('#div_zone_name_list'))
	}

	$('#div_settings_content').show();
}

save_zone_count = function() {
	$('#txt_zone_count').attr('disabled', true);
	$('#btn_save_zone_count').attr('disabled', true);

	var zone_count = $('#txt_zone_count').val();
	zone_count.replace(/[^\d]/, '');

	$.post('/save-zone-count', 'count=' + escape(zone_count))
		.done(function(result) {
			if(0 == result.error) {
				$('#div_save_success').show();

				$('#div_settings_content').show();
				rotate_refresh(0, $('#div_loading .icon-refresh'));
				$('#div_loading').show();
				fetch_zone_data();
			}
			else {
				$('#div_save_failed')
					.find('.message')
						.text(result.desc)
						.end()
					.show();
			}
		})
		.always(function(){
			$('#txt_zone_count').attr('disabled', false);
			$('#btn_save_zone_count').attr('disabled', false);
		});

}

save_zone_names = function() {
	var qs = $('#frm_zone_name').serialize();
	$('#frm_zone_name input').attr('disabled', true);

	$.post('/save-zone-names', qs)
		.done(function(result) {
			if(0 == result.error) {
				$('#div_save_success').show();
			}
			else {
				$('#div_save_failed')
					.find('.message')
						.text(result.desc)
						.end()
					.show();
			}
		})
		.always(function(){
			$('#frm_zone_name input').attr('disabled', false);
		});

}

