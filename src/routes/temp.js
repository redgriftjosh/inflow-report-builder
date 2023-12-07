const body = "This is my English Body! I guess Sentences can be separated by more than just a period, right? This is a good thing to think about... Damn I also didn't think about the three dot ending. Well, I think this is probably enough ways to split up a large body of text. I hope AI can help me out on this one.";

const story = "1701805276794x734925650322784300";

let dev = "yes";

if (dev === "yes"){
    dev = "/version-test";
} else {
    dev = "";
}

// Regular expression to split the text into sentences
const sentences = body.match(/[^\.!\?]+[\.!\?]+/g);

// Main function that ppopulates the data in bubble.io
async function processSentences() {
    // Check if sentences were found
    if (sentences) {
        for (const sentence of sentences) {
            const sentenceBody = {
                "story_custom_story": story,
                "english_sentence_text": sentence.trim()
            };
            try {
                const response = await postReq("sentence", sentenceBody, dev);
                let sentenceId = response.id;
                let sentenceIdArray = [sentenceId];
                console.log(sentenceId);
                
                const storyBody = {
                    "sentence_list_custom_sentence": [sentenceIdArray]
                };
                let patchResponse = await patchReq("story", story, storyBody, dev);
                console.log('Patchresponse', patchResponse);
                return
            } catch (error) {
                console.error('Error:', error);
            }
        }
    } else {
        console.log("No sentences found.");
    }
}

// processSentences();


async function getTest() {
    const response = await getReq("story", '1701805276794x734925650322784300', dev);
    console.log('response:', response);

}

// getTest();

async function patchTest() {
    const storyBody = {
        "sentence_list_custom_sentence": ['1701808185433x337500814266809660']
    };
    const responce = await patchReq("story", story, storyBody, dev);
}

patchTest();

async function getReq(type, id, dev) {
    const url = `https://inturruptforgetting.bubbleapps.io${dev}/api/1.1/obj/${type}/${id}`;

    const headers = {
        "Authorization": "Bearer c5993b63d8b4a0c7031a47130298d821",
        "Content-Type": "application/json"
    };

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: headers
        });
        const responseData = await response.json(); // Convert response to JSON
        return responseData;
    } catch (error) {
        console.error('Error:', error)
        throw error;
    }

}

async function postReq(type, body, dev) {
    const url = `https://inturruptforgetting.bubbleapps.io${dev}/api/1.1/obj/${type}`;

    const headers = {
        "Authorization": "Bearer c5993b63d8b4a0c7031a47130298d821",
        "Content-Type": "application/json"
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(body)
        });
        const responseData = await response.json(); // Convert response to JSON
        return responseData;
    } catch (error) {
        console.error('Error:', error)
        throw error;
    }
}

async function patchReq(type, id, body, dev) {
    const url = `https://inturruptforgetting.bubbleapps.io${dev}/api/1.1/obj/${type}/${id}`;

    const headers = {
        "Authorization": "Bearer c5993b63d8b4a0c7031a47130298d821",
        "Content-Type": "application/json"
    };

    try {
        const response = await fetch(url, {
            method: 'PATCH',
            headers: headers,
            body: JSON.stringify(body)
        });
        
        const responseData = await response.json();
        console.log(responseData);
    } catch (error) {
        console.error('Error:', error);
    }
}
