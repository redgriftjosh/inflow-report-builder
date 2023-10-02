const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

function getFileMapData() {
    const data = fs.readFileSync(path.resolve(__dirname, '../../file-map.json'), 'utf-8');
    return JSON.parse(data);
}

function saveFileMapData(data) {
    fs.writeFileSync(path.resolve(__dirname, '../../file-map.json'), JSON.stringify(data, null, 2));
}

async function newReportInFileMap(name) {
    const uniqueID = uuidv4();

    const data = getFileMapData();

    const filePath = `/Users/joshredgrift/Documents/TPI-3/Inflow/report_builder/Reports/${name}.xlsx`

    if (Object.values(data).includes(filePath)) {
        return 'File Name Already Exists';
    } else {
        data[uniqueID] = `/Users/joshredgrift/Documents/TPI-3/Inflow/report_builder/Reports/${name}.xlsx`;
        saveFileMapData(data);
        return uniqueID;
    }
}

module.exports = newReportInFileMap;

function getWorkbookPathById(id) {
    try {
        const jsonData = getFileMapData();
        const workbookPath = jsonData[id];
        if (workbookPath) {
            console.log(`Workbook path for ID ${id}: ${workbookPath}`);
            return workbookPath;
        } else {
            console.log(`No workbook found for ID ${id}`);
            return null;
        }
    } catch (error) {
        console.error(error);
    }
}

module.exports = getWorkbookPathById;