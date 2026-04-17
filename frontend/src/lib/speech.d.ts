/**
 * Full Web Speech API type declarations.
 *
 * TypeScript's built-in lib.dom.d.ts only includes SpeechRecognitionAlternative,
 * SpeechRecognitionResult, and SpeechRecognitionResultList — but NOT the main
 * SpeechRecognition interface, SpeechRecognitionEvent, or the constructor.
 *
 * This file provides all missing declarations + vendor-prefixed window properties.
 */

export {};

declare global {
  interface SpeechRecognitionEvent extends Event {
    readonly resultIndex: number;
    readonly results: SpeechRecognitionResultList;
  }

  interface SpeechRecognitionErrorEvent extends Event {
    readonly error: string;
    readonly message: string;
  }

  interface SpeechRecognition extends EventTarget {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    maxAlternatives: number;
    start(): void;
    stop(): void;
    abort(): void;
    onresult:
      | ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => void)
      | null;
    onerror:
      | ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => void)
      | null;
    onend: ((this: SpeechRecognition, ev: Event) => void) | null;
    onstart: ((this: SpeechRecognition, ev: Event) => void) | null;
  }

  declare var SpeechRecognition: {
    new (): SpeechRecognition;
  };

  interface Window {
    /** Standard constructor — available in Chrome/Edge/Safari */
    SpeechRecognition?: typeof SpeechRecognition;
    /** Vendor-prefixed constructor — legacy Chrome / older WebKit */
    webkitSpeechRecognition?: typeof SpeechRecognition;
  }
}
