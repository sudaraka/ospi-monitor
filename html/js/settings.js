
var GET_ZONE_403 = 'Server received an invalid command. Please check your network connection';
var GET_ZONE_404 = 'Server does not support the requested command';

var keep_rotating = false;

var zone_info = {};

$(function(){

	rotate_refresh(0, $('#div_loading .icon-refresh'));

	$('#btn_save_zone_count').click(save_zone_count);

	$('#btn_save_zone_names').click(save_zone_names);

	fetch_zone_data();

});

fetch_zone_data = function() {
	$.post('/get-zones')
		.done(function(data){
			zone_info = data;
			populate();
		})
		.fail(function(data){
			if(403 == data.status)
				$('#div_loading_failed .message').text(GET_ZONE_403);
			else if(404 == data.status)
				$('#div_loading_failed .message').text(GET_ZONE_404);

			$('#div_loading_failed').show('fast');

		})
		.always(function(){
			$('#div_loading').hide();
			keep_rotating = false;
		});
}

rotate_refresh = function(angle, element) {
	if(0 == angle) keep_rotating = true;

	element.css('-webkit-transform', 'rotate(' + angle + 'deg)');
	element.css('-moz-transform', 'rotate(' + angle + 'deg)');
	element.css('-o-transform', 'rotate(' + angle + 'deg)');
	element.css('-ms-transform', 'rotate(' + angle + 'deg)');

	if(keep_rotating) {
		setTimeout(function(){
			rotate_refresh(++angle, element);
		}, 5);
	}
}

populate = function() {
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
					.addClass('input-medium')
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
	zone_count.replace(/[^\d]/, '')

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

