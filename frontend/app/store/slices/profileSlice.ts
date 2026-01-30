import type { StateCreator } from "zustand";

export interface ChannelProfile {
  channel_name: string;
  avatar_key: string;
  created_at: number;
}

export interface ProfileSlice {
  // Channel Profile (persistent)
  channelProfile: ChannelProfile | null;
  channelAvatarUrl: string | null;

  // Actions
  setChannelProfile: (profile: ChannelProfile) => void;
  setChannelAvatarUrl: (url: string | null) => void;
  hasValidProfile: () => boolean;
  resetProfile: () => void;
}

const initialProfileState = {
  channelProfile: null as ChannelProfile | null,
  channelAvatarUrl: null as string | null,
};

export const createProfileSlice: StateCreator<ProfileSlice, [], [], ProfileSlice> = (set, get) => ({
  ...initialProfileState,

  setChannelProfile: (profile) =>
    set({
      channelProfile: {
        ...profile,
        created_at: profile.created_at || Date.now(),
      },
    }),

  setChannelAvatarUrl: (url) => set({ channelAvatarUrl: url }),

  hasValidProfile: () => {
    const profile = get().channelProfile;
    return !!(profile?.channel_name && profile?.avatar_key);
  },

  resetProfile: () => set(initialProfileState),
});
