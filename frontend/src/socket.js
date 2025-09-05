import { io } from 'socket.io-client';
import { BACKEND_URL } from './config';

export const socket = io(BACKEND_URL, {
  autoConnect: false, // Important: connect manually after username is set
});