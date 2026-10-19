import wordlists from './generated/wordlists.json';
import { DeviceStudio } from './device-core.js';
const studio = new DeviceStudio(wordlists, window.localStorage);
export async function deviceRequest(path, body) { return studio.request(path, body); }
