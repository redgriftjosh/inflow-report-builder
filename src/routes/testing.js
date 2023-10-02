const ExcelJS = require('exceljs');


async function addColumns() {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.readFile('/Users/joshredgrift/Documents/TPI-3/Inflow/report_builder/Reports/Testing.xlsx');
    const sheet = workbook.getWorksheet('All Data Crunch');
    
    sheet.spliceColumns(3,0,[]);

    // sheet.spliceColumns(5,0,[]);

    //sheet.getCell("A29").value = {formula: `=FILTER(A6:B23,B6:B23 = 2006, "null")`};
    //sheet.getCell("A29").value = {formula: `=SUM(B12:B13)`};
    //sheet.getCell("A29").value = `Hello World`;

    await workbook.xlsx.writeFile('/Users/joshredgrift/Documents/TPI-3/Inflow/report_builder/Reports/Testing.xlsx');
}

addColumns();