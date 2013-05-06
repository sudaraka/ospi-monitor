
var GET_ZONE_403 = 'Server received an invalid command. Please check your network connection';
var GET_ZONE_404 = 'Server does not support the requested command';

var zone_info = {};

var keep_rotating = false;

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

fetch_zone_data = function() {
	$.post('/get-zones')
		.done(function(data){
			zone_info = data;
			populate_zone_data();
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

