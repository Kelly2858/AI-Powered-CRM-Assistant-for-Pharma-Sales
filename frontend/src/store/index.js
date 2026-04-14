import { configureStore } from '@reduxjs/toolkit';
import chatReducer from './slices/chatSlice';
import interactionReducer from './slices/interactionSlice';
import hcpReducer from './slices/hcpSlice';

export const store = configureStore({
  reducer: {
    chat: chatReducer,
    interactions: interactionReducer,
    hcps: hcpReducer,
  },
});
