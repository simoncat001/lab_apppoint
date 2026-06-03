declare module '*.vue' {
    import type { DefineComponent } from 'vue'
    const component: DefineComponent<Record<string, never>, Record<string, never>, any>
    export default component
}

declare module '@wangeditor/editor-for-vue' {
    import type { DefineComponent } from 'vue'
    export const Editor: DefineComponent<any, any, any>
    export const Toolbar: DefineComponent<any, any, any>
}
