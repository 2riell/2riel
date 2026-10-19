import { invoke, isTauri } from "@tauri-apps/api/core";
import { empty, validate, type State } from "./engine";
export const desktop = isTauri();
export async function load(): Promise<State> {
  return desktop
    ? validate(JSON.parse(await invoke<string>("load_state")))
    : empty();
}
export async function save(state: State) {
  validate(state);
  if (desktop)
    await invoke("save_state", {
      json: JSON.stringify(state),
      expectedRevision: state.revision - 1,
    });
}
