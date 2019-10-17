# XGES Examples

This is a list of XGES Examples.

### Effect

``` xml
 <ges version='0.1'>
   <project properties='properties;' metadatas='metadatas;'>
     <ressources>
       <asset
        id='file:///video.mp4'
        extractable-type-name='GESUriClip' />
     </ressources>
     <timeline>
       <track
        caps='video/x-raw'
        track-type='4'
        track-id='0' />
       <layer priority='0' >
         <clip id='0'
          asset-id='file:///video.mp4'
          type-name='GESUriClip'
          layer-priority='0'
          track-types='6'
          start='0'
          duration='23901027520'
          inpoint='0' >
           <effect
            asset-id='revtv'
            clip-id='0'
            type-name='GESEffect'
            track-type='4'
            track-id='0'
            properties='properties, priority=(uint)0, active=(boolean)false, track-type=(int)4;'
            metadatas='metadatas;'
            children-properties='properties, gain=(int)100, line-space=(int)100;'>
             <binding
              type='direct'
              source_type='interpolation'
              property='line-space'
              mode='1'
              track_id='-1'
              values =' 0:1  23901027520:100 '/>
           </effect>
         </clip>
       </layer>
     </timeline>
   </project>
 </ges>
```


### Audio Volume and Alpha Keyframes


``` xml
 <ges version='0.1'>
   <project>
     <ressources>
       <asset id='file:///video.mp4' extractable-type-name='GESUriClip' />
     </ressources>
     <timeline>
       <track caps='video/x-raw' track-type='4' track-id='0' />
       <track caps='audio/x-raw' track-type='2' track-id='1' />
       <layer priority='0' >
         <clip id='0' asset-id='file:///video.mp4' type-name='GESUriClip' layer-priority='0' track-types='6' start='0' duration='10000000000' inpoint='0' >
             <binding type='direct' source_type='interpolation' property='volume' mode='1' track_id='1' values =' 0:0.0  10000000000:1.0 '/>
             <binding type='direct' source_type='interpolation' property='alpha' mode='1' track_id='0' values =' 0:0  10000000000:1 '/>
         </clip>
       </layer>
     </timeline>
 </project>
 </ges>
```


### Clip Position and Size

``` xml
 <ges version='0.1'>
   <project properties='properties;'>
     <ressources>
       <asset
          id='file:///video.mp4'
          extractable-type-name='GESUriClip' />
     </ressources>
     <timeline>
       <track caps='video/x-raw' track-type='4' track-id='0' />
       <layer priority='0'>
         <clip
            id='0'
            asset-id='file:///video.mp4'
            type-name='GESUriClip'
            layer-priority='0'
            track-types='6'
            start='0' duration='2000000000' inpoint='3000000000'
            rate='0'>
         </clip>
       </layer>
     </timeline>
   </project>
 </ges>
```

### Transition with Restriction Caps

``` xml
 <ges version='0.1'>
   <project>
     <ressources>
       <asset id='file:///video1.mp4'
          extractable-type-name='GESUriClip' />
       <asset id='file:///video2.ogg'
          extractable-type-name='GESUriClip'/>
     </ressources>
     <timeline>
       <track caps='video/x-raw' track-type='4' track-id='0' properties='properties, caps=(string)video/x-raw, restriction-caps=(string)&quot;video/x-raw\,\ width\=\(int\)720\,\ height\=\(int\)576\,\ framerate\=\(fraction\)25/1&quot;;'/>
       <track caps='audio/x-raw' track-type='2' track-id='1' />
       <layer priority='0' properties='properties, auto-transition=(boolean)true;' >
         <clip id='0'
            asset-id='file:///video1.mp4'
            type-name='GESUriClip' layer-priority='0' track-types='6'
            start='0' duration='10000000000' inpoint='0' >
         </clip>
         <clip id='3'
            asset-id='file:///video2.ogg'
            type-name='GESUriClip' layer-priority='0' track-types='6'
            start='7000000000' duration='10000000000' inpoint='5000000000' >
         </clip>
       </layer>
     </timeline>
   </project>
 </ges>
```


### Constant Layer Volume


``` xml
 <ges version='0.1'>
   <project>
     <ressources>
       <asset
        id='file:///music.flac'
        extractable-type-name='GESUriClip'
        properties='properties, supported-formats=(int)2;' />
     </ressources>
     <timeline>
       <track caps='audio/x-raw' track-type='2' track-id='0' />
       <layer priority='0' metadatas='metadatas, volume=(float)2.0;'>
         <clip id='0'
          asset-id='file:///music.flac'
          type-name='GESUriClip'
          layer-priority='0'
          track-types='2'
          start='0' duration='1000000000' inpoint='0'
          rate='0' >
         </clip>
       </layer>
       <layer priority='1' metadatas='metadatas, volume=(float)0.5;'>
         <clip id='1'
          asset-id='file:///music.flac'
          type-name='GESUriClip'
          layer-priority='1'
          track-types='2'
          start='1000000000' duration='1000000000' inpoint='1000000000'
          rate='0' >
         </clip>
       </layer>
     </timeline>
   </project>
 </ges>
```


### Encoding Profiles for MP4, WebM and OGV


``` xml
 <ges version='0.1'>
   <project>
     <encoding-profiles>
       <encoding-profile
          name='ogg'
          description=''
          type='container'
          preset-name='oggmux'
          format='application/ogg' >
         <stream-profile
            parent='ogg'
            id='0' type='video' presence='0'
            format='video/x-theora'
            preset-name='theoraenc'
            restriction='video/x-raw, width=(int)720, height=(int)576, framerate=(fraction)25/1, pixel-aspect-ratio=(fraction)1/1'
            pass='0' variableframerate='0' />
         <stream-profile
            parent='ogg' id='1' type='audio' presence='0'
            format='audio/x-vorbis'
            preset-name='vorbisenc'
            restriction='audio/x-raw, channels=(int)2, rate=(int)44100' />
       </encoding-profile>

       <encoding-profile
          name="mp4"
          description=""
          type="container"
          preset-name="qtmux"
          format="video/quicktime,variant=iso">
         <stream-profile
            parent="mp4"
            id="0"
            presence="0"
            type="video"
            preset-name="x264enc"
            format="video/x-h264"
            restriction="video/x-raw, format=I420, width=(int)1280, height=(int)720, framerate=(fraction)25/1" />
         <stream-profile
            parent="mp4"
            id="1"
            presence="0"
            type="audio"
            preset-name="lamemp3enc"
            format="audio/mpeg,mpegversion=1,layer=3"
            restriction="audio/x-raw, channels=(int)2, rate=(int)44100" />
       </encoding-profile>

       <encoding-profile
          name="webm"
          description=""
          type="container"
          preset-name="webmmux"
          format="video/webm">
         <stream-profile
            parent="webm"
            id="0"
            presence="0"
            type="video"
            preset-name="vp8enc"
            format="video/x-vp8"
            restriction="video/x-raw, width=(int)1280, height=(int)720, framerate=(fraction)25/1" />
         <stream-profile
            parent="webm"
            id="1"
            presence="0"
            type="audio"
            preset-name="vorbisenc"
            format="audio/x-vorbis"
            restriction="audio/x-raw, channels=(int)2, rate=(int)44100" />
       </encoding-profile>
     </encoding-profiles>
     <ressources>
       <asset
          id='file:///C:/Users/bmonkey/workspace/ges/data/sd/Mandelbox.mp4'
          extractable-type-name='GESUriClip' />
     </ressources>
     <timeline>
       <track caps='video/x-raw' track-type='4' track-id='0' />
       <layer priority='0'>
         <clip
            id='1'
            asset-id='file:///C:/Users/bmonkey/workspace/ges/data/sd/Mandelbox.mp4'
            type-name='GESUriClip'
            layer-priority='0'
            track-types='6'
            start='0' duration='2000000000' inpoint='0'>
         </clip>
       </layer>
     </timeline>
   </project>
 </ges>
```
