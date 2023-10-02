const ExcelJS = require('exceljs');
const newReportInFileMap = require('./file-map');
const axios = require('axios');


async function createReportHandler(req, res){
    const { name } = req.body;

    try {
        
        const reportFileMapStatus = await newReportInFileMap(name);

        if (reportFileMapStatus != 'File Name Already Exists') {
            const workbook = new ExcelJS.Workbook();
            await workbook.xlsx.readFile('/Users/joshredgrift/Documents/TPI-3/Inflow/report_builder/Templates/Template-Data-Crunch.xlsx');
        
            const worksheet = workbook.getWorksheet('Sheet1');
        
            worksheet.getCell('A1').value = 'New Value';
        
            await workbook.xlsx.writeFile('/Users/joshredgrift/Documents/TPI-3/Inflow/report_builder/Reports/'+name+'.xlsx');
            
            addReportToBubble(name, reportFileMapStatus);

            console.log('Workbook copied and modified successfully');
            res.status(200).send('Report created successfully!');
        } else {
            console.log('File Name Already Exists');
            res.status(400).send('File Name Already Exists');
        }
    } catch (error) {
        console.error('Unable to create your report: ', error);
        res.status(500).send('Failed to create report');
    }
}

module.exports = createReportHandler;


async function addReportToBubble(name, reportFileMapStatus) {
    
    try {
        const url = 'https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/Report';
        const body = {
            "Google Sheets Spreadsheet ID": reportFileMapStatus,
            "Report Name": name
        };
        const options = {
            headers : {
                "contentType": "application/json",
                "Authorization": "Bearer " + "6f8e90aff459852efde1bc77c672f6f1"
            }
        };

        const response = await axios.post(url, body, options);
        console.log('Report added to Bubble successfully:', response.data);
    } catch(error) {
        console.error('Failed to add report to Bubble:', error);
    }
}