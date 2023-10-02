const express = require('express');
const app = express();
const port = 3000;
const cors = require('cors');
const createReportHandler = require('./routes/new-report');
const addAcDataLog = require('./routes/add-ac-datalog');


app.use(cors());
app.use(express.json());

app.post('/add-ac-datalog', addAcDataLog);

app.post('/create', createReportHandler);

app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});

app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).send('Something broke!');
  });

