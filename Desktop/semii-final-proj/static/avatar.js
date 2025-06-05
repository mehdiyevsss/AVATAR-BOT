import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const container = document.getElementById("three-container");
// Set up scene with Swisscom office background
const scene = new THREE.Scene();

// Load Swisscom background image
const textureLoader = new THREE.TextureLoader();
const backgroundTexture = textureLoader.load('/static/Swisscom.jpg');
scene.background = backgroundTexture;

// Set up camera
const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);

// Set up renderer with better quality settings
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.setClearColor(0x87CEEB, 0); // Transparent background to show the image
renderer.setPixelRatio(window.devicePixelRatio);
renderer.shadowMap.enabled = true;
container.appendChild(renderer.domElement);

// Add orbit controls with restricted movement
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.screenSpacePanning = false;

// Restrict zoom range - balanced view of avatar
controls.minDistance = 2.0; // Minimum zoom distance
controls.maxDistance = 3.0; // Maximum zoom distance

// Restrict vertical rotation to keep face visible
controls.minPolarAngle = Math.PI / 4; // 45 degrees up
controls.maxPolarAngle = Math.PI / 2; // 90 degrees (horizontal)

// Restrict horizontal rotation
controls.minAzimuthAngle = -Math.PI / 4; // -45 degrees
controls.maxAzimuthAngle = Math.PI / 4;  // 45 degrees

// Disable panning to keep avatar centered
controls.enablePan = false;

// Add better lighting setup
// Main directional light (like sun)
const mainLight = new THREE.DirectionalLight(0xffffff, 1.5);
mainLight.position.set(1, 1, 2);
mainLight.castShadow = true;
scene.add(mainLight);

// Fill light from the opposite side
const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);
fillLight.position.set(-1, 0.5, -1);
scene.add(fillLight);

// Ambient light for overall scene brightness
const ambient = new THREE.AmbientLight(0xffffff, 0.7);
scene.add(ambient);

// Add a soft light from below for face illumination
const frontLight = new THREE.PointLight(0xffffff, 0.5);
frontLight.position.set(0, 0, 3);
scene.add(frontLight);

// No grid helper - clean white background

let mixer, model, mouthMesh;
let currentMouthCues = [];
let currentAudioStartTime = 0;
let isPlaying = false;

// Map mouth cue values to viseme shape keys
// This is a more comprehensive mapping for better lip sync
const visemeMap = {
  // Basic vowels
  'A': { 'viseme_aa': 1.0 }, // 'ah' as in 'father'
  'I': { 'viseme_I': 1.0 },  // 'ee' as in 'beat'
  'E': { 'viseme_E': 1.0 },  // 'eh' as in 'bet'
  'O': { 'viseme_O': 1.0 },  // 'oh' as in 'boat'
  'U': { 'viseme_U': 1.0 },  // 'oo' as in 'boot'
  
  // Consonants
  'B': { 'viseme_PP': 1.0 },  // Bilabial plosives (p, b, m)
  'F': { 'viseme_FF': 1.0 },  // Labiodental fricatives (f, v)
  'T': { 'viseme_TH': 1.0 },  // Dental fricatives (th)
  'D': { 'viseme_DD': 1.0 },  // Alveolar plosives (t, d)
  'K': { 'viseme_kk': 1.0 },  // Velar plosives (k, g)
  'CH': { 'viseme_CH': 1.0 }, // Post-alveolar affricates (ch, j)
  'S': { 'viseme_SS': 1.0 },  // Sibilant fricatives (s, z)
  'N': { 'viseme_nn': 1.0 },  // Alveolar nasals (n)
  'R': { 'viseme_RR': 1.0 },  // Alveolar approximants (r)
  
  // Special cases
  'X': {},  // Silence/neutral - all values at 0
  
  // Combined visemes for more natural transitions
  'AI': { 'viseme_aa': 0.7, 'viseme_I': 0.3 },
  'OI': { 'viseme_O': 0.7, 'viseme_I': 0.3 },
  'AU': { 'viseme_aa': 0.7, 'viseme_U': 0.3 }
};

const loader = new GLTFLoader();
loader.load('/static/brunette.glb', (gltf) => {
  model = gltf.scene;
  scene.add(model);
  
  // Position the model - hide feet completely
  model.position.set(0, -1.4, 0); // Raised higher to completely hide feet
  camera.position.set(0, 0.3, 2.8); // Adjusted camera to frame properly
  
  // Subtle arm adjustments for a natural pose
  console.log('Applying natural arm positioning');
  
  // Create a pose mixer to blend between poses
  const applyNaturalPose = () => {
    model.traverse((child) => {
      if (child.isBone) {
        const name = child.name.toLowerCase();
        
        // Left arm adjustments
        if (name.includes('left')) {
          // Shoulder/clavicle adjustments
          if ((name.includes('shoulder') || name.includes('clavicle')) && child.rotation) {
            // Adjust shoulder position
            child.rotation.x += 0.1; // Pull shoulder back
            child.rotation.y += 0.05; // Slight rotation
            child.rotation.z += 0.1; // Bring arm closer to body
          }
          
          // Upper arm adjustments
          if ((name.includes('upperarm') || (name.includes('arm') && !name.includes('forearm'))) && child.rotation) {
            // Adjust arm position
            child.rotation.x += 0.2; // Pull arm back
            child.rotation.z += 0.1; // Slight inward
          }
          
          // Forearm adjustments
          if (name.includes('forearm') || name.includes('elbow')) {
            // Slight bend at elbow
            if (child.rotation) {
              child.rotation.x += 0.1; // Pull forearm back
            }
          }
        }
        
        // Right arm adjustments
        if (name.includes('right')) {
          // Shoulder/clavicle adjustments
          if ((name.includes('shoulder') || name.includes('clavicle')) && child.rotation) {
            // Adjust shoulder position
            child.rotation.x += 0.1; // Pull shoulder back
            child.rotation.y -= 0.05; // Slight rotation
            child.rotation.z -= 0.1; // Bring arm closer to body
          }
          
          // Upper arm adjustments
          if ((name.includes('upperarm') || (name.includes('arm') && !name.includes('forearm'))) && child.rotation) {
            // Adjust arm position
            child.rotation.x += 0.2; // Pull arm back
            child.rotation.z -= 0.1; // Slight inward
          }
          
          // Forearm adjustments
          if (name.includes('forearm') || name.includes('elbow')) {
            // Slight bend at elbow
            if (child.rotation) {
              child.rotation.x += 0.1; // Pull forearm back
            }
          }
        }
      }
    });
  };
  
  // Apply the natural pose
  applyNaturalPose();
  
  // Apply a second round of adjustments after a short delay
  // This helps ensure the changes are applied properly
  setTimeout(applyNaturalPose, 100);
  
  function findMouthMesh(model) {
    // Find a mesh with morph targets for lip sync
    let headMesh = null;
    let teethMesh = null;
    let fallbackMesh = null;
    
    model.traverse((child) => {
      if (child.isMesh && child.morphTargetDictionary && Object.keys(child.morphTargetDictionary).length > 0) {
        console.log("Found mesh with morph targets:", child.name);
        console.log("Available morph targets:", child.morphTargetDictionary);
        
        // Check if this mesh has viseme morph targets
        const hasVisemes = Object.keys(child.morphTargetDictionary).some(key => key.startsWith('viseme_'));
        
        if (hasVisemes) {
          // Prioritize head or teeth meshes
          if (child.name === 'Wolf3D_Head') {
            headMesh = child;
          } else if (child.name === 'Wolf3D_Teeth') {
            teethMesh = child;
          } else {
            // Keep as fallback
            fallbackMesh = child;
          }
        }
      }
    });
    
    // Select the best mesh for lip sync in order of priority
    mouthMesh = headMesh || teethMesh || fallbackMesh;
    
    if (mouthMesh) {
      console.log("Selected mouth mesh for lip sync:", mouthMesh.name);
      console.log("Morph target dictionary:", JSON.stringify(mouthMesh.morphTargetDictionary));
      
      // Log all available morph targets for debugging
      Object.keys(mouthMesh.morphTargetDictionary).forEach(key => {
        console.log("Morph target:", key, "at index", mouthMesh.morphTargetDictionary[key]);
      });
    } else {
      console.error("No suitable mesh found for lip sync");
    }
  }
  
  findMouthMesh(model);
  
  if (!mouthMesh) {
    console.error("No mouth mesh with viseme morph targets found! Lip sync will not work.");
    // Try to find any mesh with morph targets as fallback
    model.traverse((object) => {
      if (!mouthMesh && object.isMesh && object.morphTargetDictionary) {
        mouthMesh = object;
        console.log("Using fallback mesh for lip sync:", object.name);
      }
    });
  }
  
  // Set up animation mixer
  mixer = new THREE.AnimationMixer(model);
  if (gltf.animations.length) {
    const idleAction = mixer.clipAction(gltf.animations[0]);
    idleAction.play();
  }
  
  // Start the animation loop
  animate();
}, 
(xhr) => {
  console.log((xhr.loaded / xhr.total * 100) + '% loaded');
},
(error) => {
  console.error('An error happened loading the model:', error);
});

function animate() {
  requestAnimationFrame(animate);
  if (mixer) mixer.update(0.016);
  controls.update();
  
  // Update lip sync
  if (mouthMesh && currentMouthCues.length > 0 && isPlaying) {
    const currentTime = (Date.now() - currentAudioStartTime) / 1000; // Convert to seconds
    const currentCue = currentMouthCues.find(cue => 
      currentTime >= cue.start && currentTime <= cue.end
    );
    
    if (currentCue) {
      console.log("Current viseme:", currentCue.value, "at time:", currentTime);
      applyViseme(currentCue.value);
    }
  }
  
  renderer.render(scene, camera);
}

function applyViseme(visemeValue) {
  if (!mouthMesh || !visemeMap[visemeValue]) {
    console.warn("Cannot apply viseme:", visemeValue);
    return;
  }
  
  // Reset all visemes first
  Object.keys(mouthMesh.morphTargetDictionary).forEach(key => {
    if (key.startsWith('viseme_')) {
      mouthMesh.morphTargetInfluences[mouthMesh.morphTargetDictionary[key]] = 0;
    }
  });
  
  // Apply the current viseme values from the map
  const visemeValues = visemeMap[visemeValue];
  console.log("Applying viseme:", visemeValue, "with values:", visemeValues);
  
  // Apply each morph target influence from the map
  Object.entries(visemeValues).forEach(([morphTarget, value]) => {
    const targetIndex = mouthMesh.morphTargetDictionary[morphTarget];
    if (targetIndex !== undefined) {
      console.log(`Setting ${morphTarget} to ${value}`);
      mouthMesh.morphTargetInfluences[targetIndex] = value;
    } else {
      console.warn(`Morph target not found in model: ${morphTarget}`);
    }
  });
}

async function loadMouthCues(audioUrl) {
  try {
    // Extract the audio ID from the URL
    const audioId = audioUrl.split('/').pop().split('.')[0];
    console.log("Loading mouth cues for audio ID:", audioId);
    console.log("Full audio URL:", audioUrl);
    
    // Load JSON file from the audio folder at project root
    const jsonUrl = `/audio/${audioId}.json`;
    console.log("Attempting to load JSON from:", jsonUrl);
    
    const response = await fetch(jsonUrl);
    if (!response.ok) {
      console.error(`Failed to load JSON file: ${response.status} ${response.statusText}`);
      throw new Error(`Failed to load JSON file: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log("Loaded JSON data:", data);
    
    // Handle different JSON structures
    let mouthCues = [];
    if (data.mouthCues) {
      // Standard format
      mouthCues = data.mouthCues;
    } else if (Array.isArray(data)) {
      // Array format
      mouthCues = data;
    } else if (typeof data === 'object') {
      // Try to extract visemes from any format
      mouthCues = Object.entries(data)
        .filter(([key, value]) => {
          return (typeof value === 'object' && value.start !== undefined && value.end !== undefined) ||
                 (typeof value === 'object' && value.time !== undefined);
        })
        .map(([key, value]) => {
          // Convert to standard format if needed
          if (value.time !== undefined) {
            return {
              start: value.time,
              end: value.time + 0.1, // Assume 100ms duration
              value: value.value || key
            };
          }
          return value;
        });
    }
    
    console.log("Processed mouth cues:", mouthCues);
    return mouthCues;
  } catch (error) {
    console.error("Error loading mouth cues:", error);
    // Try to load a default viseme sequence as fallback
    console.log("Attempting to use default viseme sequence");
    return [
      { start: 0, end: 0.1, value: 'B' },
      { start: 0.1, end: 0.2, value: 'A' },
      { start: 0.2, end: 0.3, value: 'B' }
    ];
  }
}

async function simulateLipSync(audio) {
  if (!mouthMesh) {
    console.error("No mouth mesh found for lip sync");
    return;
  }
  
  try {
    // Load mouth cues for this audio
    currentMouthCues = await loadMouthCues(audio.src);
    if (currentMouthCues.length === 0) {
      console.warn("No mouth cues available for lip sync, using default");
      currentMouthCues = [
        { start: 0, end: 0.1, value: 'B' },
        { start: 0.1, end: 0.2, value: 'A' },
        { start: 0.2, end: 0.3, value: 'B' }
      ];
    }
    
    // Start timing from when the audio starts
    currentAudioStartTime = Date.now();
    isPlaying = true;
    
    // Log the current state
    console.log("Lip sync initialized with cues:", currentMouthCues);
    console.log("Audio duration:", audio.duration);
    if (mouthMesh) {
      console.log("Current mouth mesh:", mouthMesh.name);
      console.log("Available morph targets:", mouthMesh.morphTargetDictionary);
    }
  } catch (error) {
    console.error("Error in simulateLipSync:", error);
    isPlaying = false;
  }
}

// Function to play audio with lip-sync
async function playAudioWithLipSync(audioUrl) {
  try {
    // Create audio element
    const audio = new Audio(audioUrl);
    
    // Load and start lip-sync when audio starts playing
    audio.onplay = () => {
      console.log("Audio started playing, starting lip-sync");
      simulateLipSync(audio);
    };
    
    // Reset mouth when audio ends
    audio.onended = () => {
      console.log("Audio ended, resetting mouth");
      currentMouthCues = [];
      isPlaying = false;
      applyViseme('X'); // Reset to silence
    };
    
    // Play the audio
    await audio.play().catch(error => {
      console.error("Error playing audio:", error);
    });
    
    return audio;
  } catch (error) {
    console.error("Error in playAudioWithLipSync:", error);
    throw error;
  }
}

// Handle window resize
window.addEventListener('resize', () => {
  const width = container.clientWidth;
  const height = container.clientHeight;
  
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  
  renderer.setSize(width, height);
});

// Check if browser supports getUserMedia
function checkMicrophoneSupport() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('Your browser does not support audio recording. Please try a different browser like Chrome or Firefox.');
    return false;
  }
  return true;
}

// Check if we're in an iframe
function isRunningInIframe() {
  try {
    return window.self !== window.top;
  } catch (e) {
    return true; // If we can't access parent window, we're definitely in an iframe
  }
}

// Request microphone permission explicitly
async function requestMicrophonePermission() {
  // Special handling for iframes
  if (isRunningInIframe()) {
    const message = 'This app is running in an iframe, which may prevent microphone access. ' +
                   'For best results, please open this app in a new browser tab.';
    console.warn(message);
    addMessage('system', message);
    
    // Create a button to open in new window
    const chatContainer = document.querySelector('.chat-section');
    if (chatContainer) {
      const openButton = document.createElement('button');
      openButton.textContent = 'Open in New Window';
      openButton.className = 'open-window-btn';
      openButton.style.marginTop = '10px';
      openButton.style.padding = '10px';
      openButton.style.background = '#4CAF50';
      openButton.style.color = 'white';
      openButton.style.border = 'none';
      openButton.style.borderRadius = '5px';
      openButton.style.cursor = 'pointer';
      openButton.onclick = () => window.open(window.location.href, '_blank');
      chatContainer.appendChild(openButton);
    }
  }
  
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true });
    return true;
  } catch (error) {
    console.error('Microphone permission error:', error);
    
    let errorMessage = '';
    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
      errorMessage = 'Microphone access was denied. Please allow microphone access in your browser settings and try again.';
    } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
      errorMessage = 'No microphone found. Please connect a microphone and try again.';
    } else if (isRunningInIframe()) {
      errorMessage = 'Microphone access is restricted in iframes. Please open this app in a new browser tab and try again.';
    } else {
      errorMessage = `Microphone error: ${error.message || 'Unknown error'}. Try refreshing the page.`;
    }
    
    addMessage('system', errorMessage);
    return false;
  }
}

// Handle recording button click
document.getElementById('recordBtn').onclick = async () => {
  const button = document.getElementById('recordBtn');
  
  // First check if microphone is supported
  if (!checkMicrophoneSupport()) return;
  
  // Request permission before starting
  const hasPermission = await requestMicrophonePermission();
  if (!hasPermission) return;
  
  button.disabled = true;
  button.textContent = 'Listening...';
  
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    const audioChunks = [];
    
    // Set up audio context for voice activity detection
    const audioContext = new AudioContext();
    const audioSource = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.4;
    audioSource.connect(analyser);
    
    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
    
    mediaRecorder.onstop = async () => {
      // Stop all tracks to release the microphone
      stream.getTracks().forEach(track => track.stop());
      audioContext.close();
      
      if (audioChunks.length > 0) {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        await processRecording(audioBlob);
      } else {
        addMessage('system', 'No audio recorded. Please try again.');
      }
      
      button.disabled = false;
      button.textContent = '🎙️ Record';
    };
    
    mediaRecorder.start(100); // Get data every 100ms
    
    // Set up voice activity detection to stop recording after silence
    let silenceStart = Date.now();
    let hasSpeaking = false;
    
    const checkAudioLevel = () => {
      if (!mediaRecorder || mediaRecorder.state !== 'recording') return;
      
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(dataArray);
      
      // Calculate audio level
      const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
      
      if (average > 20) { // There is sound
        silenceStart = Date.now();
        hasSpeaking = true;
      } else if (hasSpeaking && Date.now() - silenceStart > 1500) { // 1.5 seconds of silence
        // Stop recording
        mediaRecorder.stop();
        return;
      }
      
      // Continue checking
      requestAnimationFrame(checkAudioLevel);
    };
    
    // Start monitoring audio levels
    checkAudioLevel();
  } catch (error) {
    console.error('Error during recording:', error);
    button.disabled = false;
    button.textContent = '🎙️ Record';
    addMessage('system', `Recording error: ${error.message || 'Unknown error'}`);
  }
};

async function processRecording(audioBlob) {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.wav');
  
  try {
    // Transcribe audio
    const transcribeRes = await fetch('/transcribe', {
      method: 'POST',
      body: formData
    });
    const { transcript } = await transcribeRes.json();
    
    // Add user message to chat
    addMessage('user', transcript);
    
    // Get response
    const responseRes = await fetch('/respond', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `text=${encodeURIComponent(transcript)}`
    });
    const { response, audio_url } = await responseRes.json();
    
    // Add assistant response to chat
    addMessage('assistant', response);
    
    // Play response audio with lip-sync
    await playAudioWithLipSync(audio_url);
  } catch (error) {
    console.error('Error processing recording:', error);
  }
}

function addMessage(role, text) {
  const messagesEl = document.getElementById('messages');
  if (!messagesEl) {
    console.error('Messages container not found');
    return;
  }
  
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
} 