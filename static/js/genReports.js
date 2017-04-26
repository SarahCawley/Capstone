//loads google charts api
google.charts.load('current', {packages: ['corechart','table','calendar']});

//handle requests
function makeRequest(form,formID){
	var url = form.attr('action');
	var type = form.attr('method');
	var reportType = $('#' + formID).val();
	var data = JSON.stringify({'report':reportType});
	
	$.ajax(url, {
		type:type,
		data:data,
		contentType:'application/json',
		dataType:'json',
		
		success: function(response){			
			if(response['status'] == 200){
				//select the appropriate report to draw.
				google.charts.setOnLoadCallback(function(){
					switch(reportType){
						case '1':
							drawAllAwardsReport(response);
							break;
						case '2':
							var divID = 'manager-table';
							var responseKey = 'managers';
							var instructions = 'Select Managers(s) From Table';
							var chartTitle = 'Awards By Manager';
							drawAwardsBy(response,divID,responseKey,instructions,chartTitle);
							break;
						case '3':
							var divID = 'employee-table';
							var responseKey = 'employees';
							var instructions = 'Select Employees(s) From Table';
							var chartTitle = 'Awards By Employee';
							drawAwardsBy(response,divID,responseKey,instructions,chartTitle);
							break;
						default:
							console.log('Improper use of makeRequest() function. Valid reportIDs are 1, 2, or 3');
					}
					
				});
			}
			else{
				alert('Unable to generate report.');
			}
		},
		error: function(jqXHR,exception){
			console.log('error:');
			console.log(jqXHR);
		}
	});
}

//------------------------DOM Manipulation Functions-------------------------------------------------

//clears the div that holds the various reports
function resetReportDiv(){
	//clear report div
	$('#award-report').empty();
	$('.chart-instructions').remove();
	$('.instructions-separator').remove();
	
	//remove calendar chart div
	if($('#calendar-chart').length){
		$('#calendar-chart').remove();
		$('.chart-separator').remove();
	}
}


//resets the div that holds the calendar charts
function resetCalenderDiv(){
	$('.chart-instructions').remove();
	$('.instructions-separator').remove();
	
	//reset calendar chart
	if($('#calendar-chart').length){
		$('#calendar-chart').remove();
		$('.chart-separator').remove();
	}
}


//appends a table to the main report div in order to display multiple charts
function createTableReportDiv(divID){
	//create html to house manager table and award chart
	var htmlStr = '<table id="award-employee-table">' +
					'<tr>' +
					  '<td><div id="' + divID + '" style="border: 1px solid #ccc"></div></td>' +
					  '<td><div id="award-chart" style="border: 1px solid #ccc"></div></td>' +
					'</tr>' +
				  '</table>';
	$('#award-report').append(htmlStr);
}


//------------------------End DOM Manipulation Functions-------------------------------------------------



//------------------------Draw Chart Functions-------------------------------------------------

//get the number of years to be dispalyed in the calendar chart and set 
//the chart height accordingly
function setCalendarChartHeight(years){
	const DEFAULT_HEIGHT = 180;
	let chartRange = (Math.max.apply(null,years) - Math.min.apply(null,years)) + 1;
	
	return chartRange * DEFAULT_HEIGHT;
}


//-----All Awards Report Functions----------

//draws a pie chart that displays all awards that have been given so far
//displays a calendar chart when a piece of the pie is selected by the user
function drawAllAwardsReport(response){
	//create chart header
	let dataTable = new google.visualization.DataTable();
	dataTable.addColumn('string', 'Award');
	dataTable.addColumn('number', 'Issued On');
	
	//fill chart with data
	for(key in response){
		if(key != 'status' && key != 'dates'){
			dataTable.addRow([key,response[key]])
		}
	}
	
	//define chart type
	let chart = new google.visualization.PieChart(document.getElementById('award-report'));

	//draw chart
	let options = {
		title: 'All Awards',
		chartArea:{
			top: 20,
			width:'100%',
			height: '100%'
		}
	};
	
	chart.draw(dataTable,options);
	
	//select event function goes here
	drawAllAwardDates(chart,dataTable,response);
}


//draws calendar chart for all awards report when a specific award type is selected
function drawAllAwardDates(chart,chartData,response){
	//add select event to bar chart
	google.visualization.events.addListener(chart, 'select', function(){
		
		//reset calendar div and display chart instructions
		resetCalenderDiv();
		$('#award-report').before('<p class="chart-instructions"><strong>Select a colored segment within the pie chart to display the dates an award type was issued.<strong></p><br class="instructions-separator">');
		
		//response['dates'] index constants
		const TYPE_INDEX = 0;
		const DATE_INDEX = 1;
		const COUNT_INDEX = 2;
		
		//get selection data
		let selection = chart.getSelection();
		if(selection.length > 0){
			let type = chartData.getFormattedValue(selection[0].row,0);
			
			//create html to display chart
			$('#award-report').after("<br class='chart-separator'><br class='chart-separator'><br class='chart-separator'><div id='calendar-chart'></div>");
			
			//init chart and data table
			let calendarChartDataTable = new google.visualization.DataTable();
			let calendarChart = new google.visualization.Calendar(document.getElementById('calendar-chart'));
			
			//create chart header
			calendarChartDataTable.addColumn({type:'date',id:'Date' });
			calendarChartDataTable.addColumn({type:'number',id:'Awards granted' });
			
			//add data to table
			let years = []
			for(var i = 0; i < response['dates'].length; i++){
				let curType = response['dates'][i][TYPE_INDEX];
				if(curType === type){
					//convert date to milliseconds
					let date = new Date(Date.parse(response['dates'][i][DATE_INDEX]));
					
					//get UTC year, month and day
					//this has to be done because js assumes the date object in the GMT tz and converts to the browser's tz
					let year = date.getUTCFullYear();
					let month = date.getUTCMonth();
					let day = date.getUTCDate();
					
					if(years.indexOf(year) < 0){
						years.push(year);
					}
					//create a new date object and pass it to the calendar chart
					date = new Date(year,month,day);
					calendarChartDataTable.addRow([date,response['dates'][i][COUNT_INDEX]]);
				}
			}
			
			//draw chart
			let options = {
				title: type,
				height: setCalendarChartHeight(years),
				noDataPattern: {
					backgroundColor: '#ffffff',
					color: '#dbedda'
				 },
				 colorAxis: {
					minValue: 0,  colors: ['#9bffe6', '#0645aa']
				},
				calendar: {
					yearLabel: {
						color: '#1A8763'
					}
				}
			};

			calendarChart.draw(calendarChartDataTable, options);
		}
	});
}
					
//-----End All Awards Report Functions----------


//-----Awards By Manager/Employee Report Functions----------

//use to draw awards by manager or employee
function drawAwardsBy(response,tableDivID,responseKey,instructions,chartTitle){
	//create html to house manager table and award chart
	createTableReportDiv(tableDivID);
	
	//init number of award types to display in award chart
	let lst = [];
	for(var i = 1; i < response['awards'][0].length - 1;i++){
		lst.push(0);
	}
	
	//generate manager table rows
	let chartTable = google.visualization.arrayToDataTable(response[responseKey]);
	
	//draw manager table
	let table = new google.visualization.Table(document.getElementById(tableDivID));
	table.draw(chartTable,{width:300,height:200});
	
	//set default award chart value
	let defaultData = google.visualization.arrayToDataTable([response['awards'][0],[instructions].concat(lst).concat([''])]);
	
	//default award chart options
	chartOptions = {
		title:chartTitle,
		legend: {position: 'top', maxLines: 3},
		bar: {groupWidth: '75%'},
		isStacked: true,
		width: 800,
		height: 400,
		vAxis: {title:'Number of Awards', minValue:0, maxValue:4, format:'0'},
		animation:{startup:true,duration:900}
	};
	
	//draw default award chart
	let chart = new google.visualization.ColumnChart(document.getElementById('award-chart'));
	chart.draw(defaultData,chartOptions);
	
	//redraw bar chart when a specific manager is selected
	//redrawAwardsByManagerChart(table,chartTable,response);
	redrawAwardsBy(table,chartTable,chartTitle,response);
}


//use to redraw awards by manager or employee
//creates a select event on the table chart that will trigger the redrawing of a bar chart
//that displays the number of awards and their corresponding types given to an employee or granted by a manager
function redrawAwardsBy(table,chartTable,chartTitle,response){
	//add select event listener on manager table
	google.visualization.events.addListener(table, 'select', function(){
		//remove calendar chart
		resetCalenderDiv();
		
		//display chart instructions
		var instructions = '<p class="chart-instructions">' +
								'<strong>Select a colored segment within the bar chart to display the dates an award type was issued.</strong>' +
							'</p>' +
							'<br class="instructions-separator">';
							
		$('#award-report').before(instructions);
		
		//gets list of managers selected in the table
		let selection = table.getSelection();
		if(selection.length > 0){
			let people = [];
			for(var i = 0; i < selection.length; i++){
				people.push(chartTable.getFormattedValue(selection[i].row,0));
			}
			
			//get data for selected managers
			let newInfo = [response['awards'][0]];
			for(var i = 1; i < response['awards'].length; i++){
				if(people.indexOf(response['awards'][i][0]) != -1){
					newInfo.push(response['awards'][i]);
				} 
			}
			
			//redraw award chart
			let chartData = google.visualization.arrayToDataTable(newInfo);
			chart = new google.visualization.ColumnChart(document.getElementById('award-chart'));
			
			chartOptions = {
				title:chartTitle,
				legend: { position: 'top', maxLines: 3 },
				bar: { groupWidth: '75%' },
				isStacked: true,
				width: 800,
				height: 400,
				vAxis: {title:'Number of Awards',minValue:4, viewWindow:{min:0},format:'0'},
				animation:{startup:true,duration:900}
			};
			
			chart.draw(chartData,chartOptions);
			
			//clean up newInfo array
			newInfo.splice(1,newInfo.length);
			
			//call calendar chart maker
			//displayAwardsByManagerDates(chart,chartData,response);
			drawAwardsByDate(chartData,response);
		}
	});
}


//use to draw a calendar chart that displays when an award type selected from the bar chart was granted/received
function drawAwardsByDate(chartData,response){
	//add select event to bar chart
	google.visualization.events.addListener(chart, 'select', function(){
			
		//reset calendar chart
		resetCalenderDiv();
		
		//display chart instructions
		var instructions = '<p class="chart-instructions">' +
								'<strong>Select a colored segment within the bar chart to display the dates an award type was issued.</strong>' +
							'</p>' +
							'<br class="instructions-separator">';
							
		$('#award-report').before(instructions);
		
		//response['dates'] index constants
		const FNAME_INDEX = 0;
		const LNAME_INDEX = 1;
		const TYPE_INDEX = 2;
		const DATE_INDEX = 3;
		const COUNT_INDEX = 4;
		
		//get selection data
		let selection = chart.getSelection();
		
		if(selection.length > 0 && selection[0].row != null){
			let name = chartData.getFormattedValue(selection[0].row,0);
			let awardType = chartData.getColumnLabel(selection[0].column);
			
			//create html to display chart
			$('#award-report').after("<br class='chart-separator'><br class='chart-separator'><div id='calendar-chart'></div>");
			
			//init chart and data table
			let calendarChartDataTable = new google.visualization.DataTable();
			let calendarChart = new google.visualization.Calendar(document.getElementById('calendar-chart'));
			
			//create chart header
			calendarChartDataTable.addColumn({type:'date',id:'Date' });
			calendarChartDataTable.addColumn({type:'number',id:'Awards granted' });
			
			//add data to table
			let years = []
			for(var i = 0; i < response['dates'].length; i++){
				let curName = response['dates'][i][FNAME_INDEX] + ' ' + response['dates'][i][LNAME_INDEX];
				let curType = response['dates'][i][TYPE_INDEX];
				if((curName === name) && (curType === awardType)){
					//convert date to milliseconds
					let date = new Date(Date.parse(response['dates'][i][DATE_INDEX]));
					
					//get UTC year, month and day
					//this has to be done because js assumes the date object in the GMT tz and converts to the browser's tz
					let year = date.getUTCFullYear();
					let month = date.getUTCMonth();
					let day = date.getUTCDate();
					
					if(years.indexOf(year) < 0){
						years.push(year);
					}
					//create a new date object and pass it to the calendar chart
					date = new Date(year,month,day);
					calendarChartDataTable.addRow([date,response['dates'][i][COUNT_INDEX]]);
				}
			}
			
			//draw chart
			let options = {
				title: awardType,
				height: setCalendarChartHeight(years),
				noDataPattern: {
					backgroundColor: '#ffffff',
					color: '#dbedda'
				 },
				 colorAxis: {
					minValue: 0,  colors: ['#9bffe6', '#0645aa']
				},
				calendar: {
					yearLabel: {
						color: '#1A8763'
					}
				}
			};

			calendarChart.draw(calendarChartDataTable, options);
		}
	});
}

//-----End Awards By Manager/Employee Report Functions----------


//------------------------End Draw Chart Functions-------------------------------------------------
// handle reports
$(document).ready(function(){
	//all awards report (1)
	$('#all-awards-form').on('submit',function(){
		event.preventDefault();
		
		//reset report div and display instructions
		resetReportDiv();
		$('#award-report').before('<p class="chart-instructions"><strong>Select a colored segment within the pie chart to display the dates an award type was issued.<strong></p><br class="instructions-separator">');
		
		var form = $(this);
		makeRequest(form,'all-awards-report');
	});
	
	
	//awards by manager report (2)
	$('#award-by-manager-form').on('submit',function(){
		event.preventDefault();
		
		//clear report div and display instructions
		resetReportDiv();
		var instructions = '<p class="chart-instructions">' +
								'<strong>Select a manager from the table to view the awards they have granted</strong>' +
							'</p>' +
							'<br class="instructions-separator">';
							
		$('#award-report').before(instructions);
		
		var form = $(this);
		makeRequest(form,'award-by-manager');
		
	});
	
	
	//awards by employee report (3)
	$('#award-by-employee-form').on('submit',function(){
		event.preventDefault();
		
		//clear report div and display instructions
		resetReportDiv();
		var instructions = '<p class="chart-instructions">' +
								'<strong>Select an employee from the table to view the awards they have received</strong>' +
							'</p>' +
							'<br class="instructions-separator">';
							
		$('#award-report').before(instructions);
		
		var form = $(this);
		makeRequest(form,'award-by-employee');
	});
});