import type { CSSProperties } from 'react';
const paths:Record<string,string[]>={
 home:['M3 10 12 3l9 7','M5 9v12h5v-7h4v7h5V9'],
 send:['m22 2-7 20-4-9-9-4 20-7Z','m22 2-11 11'],
 receipt:['M6 3h12v18l-3-2-3 2-3-2-3 2V3Z','M9 7h6','M9 11h6','M9 15h3'],
 people:['M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2','M16 3a4 4 0 0 1 0 8','M22 21v-2a4 4 0 0 0-3-3.87','M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0'],
 chart:['M4 3v17h17','M8 16V9','M13 16V5','M18 16v-6'],
 bell:['M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9','M10 21h4'],
 plus:['M12 5v14','M5 12h14'], close:['m6 6 12 12','M18 6 6 18'],
 check:['m5 12 4 4L19 6'], arrow:['M5 12h14','m13 6 6 6-6 6'], back:['M19 12H5','m11 6-6 6 6 6'],
 shield:['m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z','m8 12 3 3 5-6'],
 wallet:['M20 8V5H5a3 3 0 0 0 0 6h16v8H5a3 3 0 0 1-3-3V8','M21 11h-5v5h5'],
 settings:['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8','M12 2v3','M12 19v3','M2 12h3','M19 12h3','m5 5 2 2','m17 17 2 2','m5 19 2-2','m17 7 2-2'],
 logout:['M9 21H4V3h5','M9 12h12','m17 8 4 4-4 4'],
 download:['M12 3v12','m7 10 5 5 5-5','M5 16v5h14v-5'],
 upload:['M12 16V4','m7 9 5-5 5 5','M4 17v4h16v-4'],
 search:['M21 21l-5-5','M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0'],
 clock:['M12 8v4l3 2','M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
 savings:['M5 10a7 7 0 0 1 12-4l3-1v5l2 1v5h-3l-1 4h-3v-3H9v3H6l-1-5H2v-5h3','M10 6h4'],
 mail:['M3 5h18v14H3V5Z','m3 6 9 6 9-6'], info:['M12 11v6','M12 7h.01','M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
};
export default function Icon({name,size=20,style}:{name:string;size?:number;style?:CSSProperties}) {
 return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={style}>{(paths[name]||paths.info).map((d,i)=><path key={i} d={d}/>)}</svg>;
}
