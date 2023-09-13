const ExcelJS = require('exceljs');
const express = require('express');
const app = express();
const port = 3000;
const cors = require('cors');
app.use(cors());

app.use(express.json());

app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});

app.post('/create-report',(req, res) => {
    const { name } = req.body;
    createNewDoc(name)
        .then(() => {
            res.status(200).send('Report created successfully!');
        })
        .catch((error) => {
            console.error('Error creating your report: ', error);
            res.status(500).send('Failed to create report');
        });
});

app.post('/update-ac',(req, res) => {
    const { name } = req.body;
    createNewDoc(name)
        .then(() => {
            res.status(200).send('Report created successfully!');
        })
        .catch((error) => {
            console.error('Error creating your report: ', error);
            res.status(500).send('Failed to create report');
        });
});

app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).send('Something broke!');
  });

//Creates a new document from the template
async function createNewDoc(name){
    try{
        const workbook = new ExcelJS.Workbook();
        await workbook.xlsx.readFile('/Users/joshredgrift/Documents/TPI-3/Inflow/report_builder/Template.xlsx');
    
        const worksheet = workbook.getWorksheet('Sheet1');
    
        worksheet.getCell('A1').value = 'New Value';
    
        await workbook.xlsx.writeFile('/Users/joshredgrift/Documents/TPI-3/Inflow/report_builder/'+name+'.xlsx');
    
        console.log('Workbook copied and modified successfully');
    } catch (error) {
        throw error;
    }
}
