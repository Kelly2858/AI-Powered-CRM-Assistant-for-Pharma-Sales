import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

export const fetchInteractions = createAsyncThunk(
  'interactions/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const response = await axios.get(`${API_URL}/interactions`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch');
    }
  }
);

export const fetchInteraction = createAsyncThunk(
  'interactions/fetchOne',
  async (id, { rejectWithValue }) => {
    try {
      const response = await axios.get(`${API_URL}/interactions/${id}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch');
    }
  }
);

export const deleteInteraction = createAsyncThunk(
  'interactions/delete',
  async (id, { rejectWithValue }) => {
    try {
      await axios.delete(`${API_URL}/interactions/${id}`);
      return id;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to delete');
    }
  }
);

const initialFormData = {
  hcp_name: '', interaction_type: 'Meeting',
  date: new Date().toISOString().split('T')[0],
  time: new Date().toTimeString().slice(0, 5),
  sentiment: 'Neutral',
  attendees: '', materials_shared: '', samples_distributed: '', topics_discussed: '',
  outcomes: '', follow_up_actions: '', summary: '',
};

const interactionSlice = createSlice({
  name: 'interactions',
  initialState: {
    list: [],
    current: null,
    loading: false,
    error: null,
    formData: initialFormData,
  },
  reducers: {
    clearCurrent: (state) => {
      state.current = null;
    },
    updateFormData: (state, action) => {
      const filteredPayload = { ...action.payload };
      for (const key in filteredPayload) {
        const val = filteredPayload[key];
        if (val === '' || val === null || (Array.isArray(val) && val.length === 0)) {
          delete filteredPayload[key];
        }
      }
      state.formData = { ...state.formData, ...filteredPayload };
    },
    clearFormData: (state) => {
      state.formData = initialFormData;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchInteractions.pending, (state) => { state.loading = true; })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.loading = false;
        state.list = action.payload;
      })
      .addCase(fetchInteractions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchInteraction.fulfilled, (state, action) => {
        state.current = action.payload;
      })
      .addCase(deleteInteraction.fulfilled, (state, action) => {
        state.list = state.list.filter((i) => i.id !== action.payload);
      });
  },
});

export const { clearCurrent, updateFormData, clearFormData } = interactionSlice.actions;
export default interactionSlice.reducer;
