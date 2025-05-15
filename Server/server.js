require('dotenv').config();
const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const pinataSDK = require('@pinata/sdk');

const app = express();
const PORT = process.env.PORT || 3005;

// Middleware
app.use(cors());
app.use(bodyParser.json());

const pinata = new pinataSDK({ 
  pinataJWTKey: process.env.PINATA_JWT,
  pinataGateway: "plum-tough-mongoose-147.mypinata.cloud"
});

// Function to upload image to IPFS
async function uploadImageToIPFS(imagePath, name, description) {
  try {
    console.log(`Uploading image ${imagePath} to IPFS...`);
    
    // Create a readable stream from the file
    const readableStreamForFile = fs.createReadStream(imagePath);
    const fileName = name || path.basename(imagePath);
    
    const options = {
      pinataMetadata: {
        name: fileName,
        description: description || `Sensor image uploaded at ${new Date().toISOString()}`
      },
      pinataOptions: {
        cidVersion: 0
      }
    };
    
    // Upload the file to IPFS
    const result = await pinata.pinFileToIPFS(readableStreamForFile, options);
    
    const imageUrl = `https://gateway.pinata.cloud/ipfs/${result.IpfsHash}`;
    console.log(`Image uploaded to IPFS: ${imageUrl}`);
    
    // Return only the image URL
    return { imageUrl };
  } catch (error) {
    console.error('Error uploading to IPFS:', error);
    throw error;
  }
}

// API endpoint to process sensor data 
app.post('/api/upload-image', async (req, res) => {
  try {
    const { temperature, humidity, imagePath } = req.body;
    
    if (temperature === undefined || humidity === undefined) {
      return res.status(400).json({ 
        success: false,
        error: 'Missing required fields (temperature and humidity)' 
      });
    }
    
    // Optional image handling
    let imageUrl = null;
    if (imagePath) {
      // Construct the full path to the image
      const fullImagePath = path.join('/home/hariz/Desktop/AgroX-IoT/RaspberryPi', imagePath);
      
      if (fs.existsSync(fullImagePath)) {
        const ipfsData = await uploadImageToIPFS(
          fullImagePath, 
          `Sensor Data Image`, 
          `Sensor data: Temp ${temperature}°C, Humidity ${humidity}%`
        );
        imageUrl = ipfsData.imageUrl;
        console.log(`IPFS image URL: ${imageUrl}`);
      } else {
        console.warn(`Image file not found: ${fullImagePath}`);
        return res.status(404).json({
          success: false,
          error: 'Image file not found'
        });
      }
    }
    
    // Prepare data response
    const sensorData = {
      temperature,
      humidity,
      imageUrl,
      timestamp: new Date().toISOString()
    };
    
    // Return the prepared data
    return res.status(200).json({ 
      success: true, 
      message: 'Data processed successfully',
      data: sensorData
    });
  } catch (error) {
    console.error('Error processing sensor data:', error);
    return res.status(500).json({ 
      success: false,
      error: error.message 
    });
  }
});

// API endpoint to check server status
app.get('/api/status', (req, res) => {
  res.status(200).json({ 
    status: 'online', 
    timestamp: new Date().toISOString()
  });
});

// Start the server
app.listen(PORT, () => {
  console.log(`AgroX Server running on port ${PORT}`);
  console.log(`API endpoints:`);
  console.log(`- POST /api/sensor-data - To process sensor data and images`);
  console.log(`- GET /api/status - To check server status`);
});
