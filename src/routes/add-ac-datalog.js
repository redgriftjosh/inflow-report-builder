const ExcelJS = require('exceljs');
const axios = require('axios');
const Papa = require('papaparse');
const getWorkbookPathById = require('./file-map');

//This is initiated from the index script by the post request coming in. It takes the csv and parses it to a nested array.
async function addAcDataLog(req, res) {
    const { file, spreadsheet_id, ac_data_logger_id } = req.body;
    const filePath = getWorkbookPathById(spreadsheet_id);
    
    //so every time I update the template by adding or removing rows, I only need to update this number rather than go through and update every formula's starting row.
    const startRow = 29;

    const response = await axios.get(file);
    const csvContent = response.data;
    Papa.parse(csvContent, {
        complete: (csvData) => {
            console.log("Parsed result:", csvData.data);
            addColumns(ac_data_logger_id, filePath, csvData.data, startRow);
            //formatForBubble(csvData.data, ac_data_logger_id);
        },
        error: (error) => {
            console.error("Parsing error:", error);
        }
    });

    res.status(200).send('Success');

}

module.exports = addAcDataLog;

//takes the csv array and formats it into a json string of less than 200 entries because that is bubbles limit.
function formatForBubble(csvData, ac_data_logger_id) {
    const csvRows = csvData.length;
    const interval = Math.floor(csvRows / 100); // Equidistant interval
    
let jsonString = "";

    if (csvRows <= 199) {
        const jsonRows = [];
        for (let i = 1; i < csvData.length; i++) { // Start from index 1 to exclude header
            const jsonRow = {
                "Date": csvData[i][0],
                "Amps": csvData[i][1],
                "AC-Data-Logger": ac_data_logger_id
            };
            jsonRows.push(jsonRow);
        }
        jsonString = jsonRows.map(function(row) {
            return JSON.stringify(row) + "\n";
        }).join("");
        console.log(jsonString);
    } else {
        const jsonRows = [];
        for (let i = 1; i < csvData.length; i += interval) {
            const jsonRow = {
                "Date": csvData[i][0],
                "Amps": csvData[i][1],
                "AC-Data-Logger": ac_data_logger_id
            };
            jsonRows.push(jsonRow);
        }
        jsonString = jsonRows.map(function(row) {
            return JSON.stringify(row) + "\n";
        }).join("");
        console.log(jsonString);
    }

    updateAcLogEntry(jsonString, ac_data_logger_id);
}

//sends the post request to bubble with the csv content formatted into less than 200 json entries to update the graph on the front end.
//Also formats the reponse from bubble after sending the webhook to extract the id's of each entry
async function updateAcLogEntry(jsonString, ac_data_logger_id) {
    const url = "https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/AC-Log-Entry/bulk";
    const body = jsonString;
  
    try {
      const response = await axios.post(url, body, {
        headers: {
          "Content-Type": "text/plain",
          "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1"
        }
      });
  
      console.log(response.data);
  
      const responseText = response.data;
      const responseArray = responseText.trim().split("\n");
  
      const responseData = responseArray.map((entry) => JSON.parse(entry));
  
      const ids = responseData.map((entry) => entry.id);
      updateDataLogId(ids, ac_data_logger_id);

      console.log(ids);
    } catch (error) {
      console.error(error);
    }

  }
//takes the id's of each entry and adds them to the appropriate data logger object in bubble.io through patch request.
async function updateDataLogId(ids,ac_data_logger_id) {
    const url = "https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/AC-Data-Logger/"+ac_data_logger_id;
    const body = {
        "AC-Log-Entry": ids
    };

    try {
        const response = await axios.patch(url, body, {
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1"
            }
        });
        console.log(response.data);
    } catch (error) {
        console.error(error);
    }
}


async function addColumns(ac_data_logger_id, filePath, csvData, startRow) {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.readFile(filePath);

    const sheetDataCrunch = workbook.getWorksheet('All Data Crunch');


    let lastColumnInRow24 = 1;
    let row24 = sheetDataCrunch.getRow(24);

    row24.eachCell((cell, colNumber) => {
        if(cell.text) {
            lastColumnInRow24 = colNumber;
        }
    });
    console.log("Last column in row 24: " + lastColumnInRow24);
    const sheetDataLogger = workbook.addWorksheet(`ACD ${lastColumnInRow24}`);
    
    sheetDataLogger.columns = [
        { key: 'A', style: { numFmt: 'MM/DD/YYYY HH:MM:SS AM/PM' } },
      ];

    csvData.forEach((row, index) => {
        row[1] = parseFloat(row[1]);
        sheetDataLogger.addRow(row);
    });
  
    //the template comes with a spot for one Air Contitioner so only create new columns if there's already one.
    if (lastColumnInRow24 > 1) {
        //Creates the new column for Amps
        console.log("Creating amps column");
        sheetDataCrunch.spliceColumns(lastColumnInRow24+1,0,[]);

        console.log("Creating kWs column");
        sheetDataCrunch.spliceColumns(lastColumnInRow24*2+1,0,[]);
   
        console.log("Creating ACFM column");
        sheetDataCrunch.spliceColumns(lastColumnInRow24*3+2,0, []);

        //Adds csv data to the new document.
        // for (let i = 1; i < csvData.length; i++) {
        //     let parsedValue = parseFloat(csvData[i][1]);
        //     sheetDataCrunch.getCell(i + 27, lastColumnInRow24 + 1).value = parsedValue;
        // }
        
        
    } else {
        console.log("Running the else statement!")
        const lastRow = sheetDataLogger.lastRow._number;
        sheetDataCrunch.getCell(startRow, 1).value = `=IF(AND(B2<>"",B3<>""), FILTER('ACD 1'!A2:B${lastRow}, ('ACD 1'!A2:A${lastRow} >= B2) * ('ACD 1'!A2:A${lastRow} <= B3),""), FILTER('ACD 1'!A2:B${lastRow}, 'ACD 1'!B2:B${lastRow},""))`;
        //sheetDataCrunch.getCell(startRow, 4).value = { formula: '=IF(AND(B2<>"",B3<>""), FILTER('ACD 1'!A2:B100, ('ACD 1'!A2:A100 >= B2) * ('ACD 1'!A2:A100 <= B3),""), FILTER('ACD 1'!A2:B100, 'ACD 1'!B2:B100,""))' };
        //sheetDataCrunch.getCell(startRow, 3).value = `hi`;
        //Adds csv data to the new document.
        // csvData.forEach((row, index) => {
        //     if (index !== 0) {
        //         row[1] = parseFloat(row[1]);
        //         sheetDataCrunch.addRow(row);
        //     }
        // });
        
    }

    //adds ac_data_logger_id to the row of ac_data_logger_ids
    sheetDataCrunch.getCell(24, lastColumnInRow24+1).value = `ACD ${lastColumnInRow24}`;
    sheetDataCrunch.getCell(25, lastColumnInRow24+1).value = ac_data_logger_id;
    //updateKwFormula(sheetDataCrunch, lastColumnInRow24, startRow);
    await workbook.xlsx.writeFile(filePath);
}

async function updateKwtFormula(sheetDataCrunch, lastColumnInRow24) {
    const lastRow = sheetDataCrunch.lastRow._number;

}

async function updateKwFormula(sheetDataCrunch, lastColumnInRow24, startRow) {
    // const workbook = new ExcelJS.Workbook();
    // await workbook.xlsx.readFile(filePath);
    // const sheetDataCrunch = workbook.getWorksheet('All Data Crunch');
    const lastRow = sheetDataCrunch.lastRow._number;

    for (let i = startRow-1; i <= lastRow; i++) {
        sheetDataCrunch.getCell(i+1, lastColumnInRow24*2+1).value = { formula: `=MIN(ROUND(B${i + 1}*B$20*IF(B${i + 1}<B$23,B$22,B$21)*SQRT(3)/1000,2),B$13*0.746)`};
    }

}

async function addDataLogSheet(ac_data_logger_id, filePath, csvData) {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.readFile(filePath);
    const worksheet = workbook.addWorksheet('ADL' + ac_data_logger_id);

    csvData.forEach((row, index) => {
        worksheet.addRow(row);
    });

    await workbook.xlsx.writeFile(filePath);
}
