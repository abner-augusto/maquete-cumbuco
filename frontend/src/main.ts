import '@fontsource/cinzel/500.css';
import '@fontsource/cinzel/600.css';
import '@fontsource/jost/400.css';
import '@fontsource/jost/500.css';
import '@fontsource/jost/600.css';
import './estilos/base.css';
import './estilos/temas/americas.css';
import { mount } from 'svelte';
import App from './App.svelte';

mount(App, { target: document.getElementById('app')! });
