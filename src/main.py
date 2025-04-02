import time
import flet as ft
from utils import config,cap_tools
import pyautogui
import cv2
import base64
from ultralytics import YOLO
from cvzone.HandTrackingModule import HandDetector
from cvzone.FPS import FPS

pyautogui.PAUSE=0.1

SC_WIDTH,SC_HEIGHT=pyautogui.size()

fpsReader=FPS(avgCount=30)

model=YOLO(model="models/int8_640px_openvino_model")

detector=HandDetector(staticMode=False,maxHands=2,modelComplexity=1,detectionCon=0.5,minTrackCon=0.5)

class status:
    value:bool
    def __init__(self):
        self.value=False

def main(page: ft.Page):

    debug_listview=ft.ListView(expand=1,spacing=10,padding=20,auto_scroll=True)
    def debug_txt(test):
        debug_listview.controls.append(ft.Text(test))
        page.update()
    def debug_type_list(test_list):
        for test in test_list:
            print(f"type:{type(test)}->value:{test}")

    def on_keyboard(e:ft.KeyboardEvent):
        debug_txt(f"Key:{e.key},Shift:{e.shift},Control:{e.ctrl},Alt:{e.alt},Meta:{e.meta}")

    page.on_keyboard_event=on_keyboard

    def route_change(route):
        page.views.clear()
        page.views.append(
            ft.View(
                "/",
                [
                    ft.AppBar(
                        title=ft.Text("Hand Controller"),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        actions=[
                            ft.IconButton(
                                icon=ft.Icons.SETTINGS,
                                on_click=lambda _: (model_cancel_pressed(stop_model_button),page.go("/settings")),
                            ),
                        ],
                    ),
                    show_panel,
                    ft.Row(
                        controls=[
                            model_button_switcher,
                        ],
                        # spacing=1
                    ),
                    ft.Divider(),
                    image,
                    debug_listview,
                ],
            )
        )

        if page.route == "/settings":
            page.views.append(
                ft.View(
                    "/settings",
                    [
                        ft.AppBar(title=ft.Text("settings"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
                        camera_setting_panel,
                        model_setting_panel,
                        model_task_panel,
                    ],
                )
            )
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)

    def animate_model_switcher(e):
        model_button_switcher.content=e
        page.update()

    def model_cancel_pressed(e):
        animate_model_switcher(run_model_button)
        status.value=False

    def model_keypoint_tracker(frame):
        hands,frame=detector.findHands(frame,draw=show_switch.value and show_all_keypoint_checkbox.value,flipType=show_flipType.value)
        if hands:
            for hand in hands:
                lmList=hand["lmList"] #21 keypoint
                bbox=hand["bbox"]#bounding box
                center=hand["center"]# center position
                form=hand["type"]# "Left" or "Right"

            if show_keypoint_id.value:
                for i,value in enumerate(lmList):
                    x,y,z=value
                    cv2.circle(frame,(x,y),2,(255,0,0),1)
                    cv2.putText(frame,str(i),(x,y),cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,255,255),2,cv2.LINE_AA)

        return hands

    def model_gesture_detect(frame):
        results=model(frame,imgsz=int(model_imgsz.value),iou=float(model_iou.value),conf=float(model_conf.value))
        return results
        # for result in results:
        #     arr=result.boxes.numpy()
        #     names = [result.names[cls.item()] for cls in result.boxes.cls.int()]  # class name of each box
        #     nums=list(map(lambda x:x.item(),result.boxes.cls.int()))
        #     confs = result.boxes.conf  # confidence score of each box
        #     if arr.xyxy.size and show_switch.value and show_gesture_checkbox.value:
        #         position=list(map(int,arr.xyxy[0]))
        #         cv2.rectangle(frame,position[0:2],position[2:4],(11,255,14),2)
        #         cv2.putText(frame,f"{nums}"+"{} | {:.2f}".format(names[0],arr.conf[0]),position[0:2], cv2.FONT_HERSHEY_DUPLEX,1,(0,0,255),1,cv2.LINE_AA)

    def model_run_pressed(e):
        animate_model_switcher(stop_model_button)
        status.value=True

        cap=cv2.VideoCapture(int(camera_id.value))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,int(camera_width.value))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT,int(camera_height.value))
        last=""
        
        
        while True and page.window.on_event!="close" and status.value:

            success,frame=cap.read()
            if not success:
                print("Can not find camera")
                break

            frame=cv2.flip(frame,1)

            if show_switch.value and show_fps_checkbox.value:
                fps,frame=fpsReader.update(frame,pos=(0,20),bgColor=(0,255,0),textColor=(0,0,255),scale=2,thickness=2)

            hands=model_keypoint_tracker(frame)

            results=model_gesture_detect(frame)

            for result in results:
                arr=result.boxes.numpy()
                names = [result.names[cls.item()] for cls in result.boxes.cls.int()]  # class name of each box
                nums=list(map(lambda x:x.item(),result.boxes.cls.int()))
                confs = result.boxes.conf  # confidence score of each box
                if names:
                    now=names[0]
                    if show_switch.value and show_gesture_checkbox.value:
                        position=list(map(int,arr.xyxy[0]))
                        cv2.rectangle(frame,position[0:2],position[2:4],(11,255,14),2)
                        cv2.putText(frame,f"{nums}"+"{} | {:.2f}".format(names[0],arr.conf[0]),position[0:2], cv2.FONT_HERSHEY_DUPLEX,1,(0,0,255),1,cv2.LINE_AA)
                    
                    always=config.GESTURE_NAME.ALL.value
                    for e in list(map(lambda x:x.content.controls,list(filter(lambda x:x.data,task_item_list.controls)))):
                        last_name,now_name,k_id,mouse_task,mouse_name=list(map(lambda x:x.value,e))
                        if last_name==always and now_name==always:
                            handle_mouse_task(mouse_task,mouse_name,hands[0]["lmList"][k_id][0:2] if hands else None)
                            debug_txt(hands[0]["lmList"][k_id])
                        elif last_name==always and last!=now_name and now==now_name:
                            handle_mouse_task(mouse_task,mouse_name,hands[0]["lmList"][k_id][0:2] if hands else None)
                        elif now_name==always and last==last_name and now!=last_name:
                            handle_mouse_task(mouse_task,mouse_name,hands[0]["lmList"][k_id][0:2] if hands else None)
                        elif last==last_name and now==now_name:
                            handle_mouse_task(mouse_task,mouse_name,hands[0]["lmList"][k_id][0:2] if hands else None)
                        
                    last=now
                
            image.src_base64=base64.b64encode(cv2.imencode('.jpg',frame)[1]).decode("utf-8")
            page.update()

        image.src_base64=config.Image_64.DEFAULT.value
        cap.release()
        page.update()

    # page basic info
    page.title="Hand Controller"
    page.auto_scroll=True
    page.window.height=900
    page.window.width=700

    # main home view
    image=ft.Image(src_base64=config.Image_64.DEFAULT.value,fit=ft.ImageFit.CONTAIN)

    stop_model_button=ft.FloatingActionButton(icon=ft.Icons.CANCEL,on_click=model_cancel_pressed,bgcolor=ft.Colors.RED_100)
    run_model_button=ft.FloatingActionButton(icon=ft.Icons.PLAY_ARROW,on_click=model_run_pressed,bgcolor=ft.Colors.BLUE_100)
    model_button_switcher=ft.AnimatedSwitcher(
        content=run_model_button,
        transition=ft.AnimatedSwitcherTransition.FADE,
        duration=500,
        reverse_duration=100,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
    )

    show_switch=ft.Switch(label="",value=False)
    show_fps_checkbox=ft.Checkbox(label="Show FPS on frame",value=False)
    show_all_keypoint_checkbox=ft.Checkbox(label="Show all keypoints on hands",value=False)
    show_keypoint_id=ft.Checkbox(label="Show keypoint ID on hands",value=False)
    show_flipType=ft.Checkbox(label="Show flipType(change the left and right)",value=False)
    show_gesture_checkbox=ft.Checkbox(label="Show gesture class and configture on the frame",value=False)

    show_panel=ft.ExpansionTile(
        title=ft.Row(controls=[
            ft.Text("Show"),
            show_switch
        ]),
        subtitle=ft.Text("This draws the visual results on the frame"),
        controls=[
            show_fps_checkbox,
            show_all_keypoint_checkbox,
            show_keypoint_id,
            show_flipType,
            show_gesture_checkbox,
        ],
    )

    # settings view
    # camera setting
    def sync_data(e:ft.TextField,func):
        e.data=func(e.value)
        debug_type_list(e.value)
        debug_type_list(e.data)
    def list_col_fit(e):
        for i in e:i.col={"sm":6,"md":4,"xl":2}
        return e

    camera_id=ft.DropdownM2(
        label="ID",
        value=cap_tools.cap_available()[0],
        tooltip="Switch the available",
        options=list(map(lambda x:ft.dropdownm2.Option(x),cap_tools.cap_available())),
        autofocus=True,
    )
    camera_width=ft.TextField(
        label="Width",
        value=640,
    )
    camera_height=ft.TextField(
        label="Height",
        value=480,
    )
    camera_fps=ft.TextField(
        label="FPS",
        value=30,
    )
    camera_setting_panel=ft.ExpansionTile(
        title=ft.Text("Camera"),
        subtitle=ft.Text("Change basic settings for camera"),
        controls=[
            ft.Divider(),
            ft.ResponsiveRow(controls=list_col_fit([camera_id,camera_width,camera_height,camera_fps]))
        ]
    )
    # model setting
    model_device=ft.DropdownM2(
        label="Device",
        value="cpu",
        options=[
            ft.dropdownm2.Option("cpu"),
            ft.dropdownm2.Option("gpu"),
        ]
    )
    model_imgsz=ft.TextField(
        value=320,
        label="Image Size",
    )
    model_iou=ft.TextField(
        value=0.55,
        label="iou",
    )
    model_conf=ft.TextField(
        value=0.5,
        label="Confidence",
    )
    model_setting_panel = ft.ExpansionTile(
        title=ft.Text("Model"),
        subtitle=ft.Text("Change basic settings for model"),
        controls=[
            ft.Divider(),
            ft.ResponsiveRow(
                controls=list_col_fit([model_device,model_imgsz,model_iou,model_conf])
            ),
        ],
    )

    # 手势条件      class(id)
    # 关键点条件    position(x,y)
    # 鼠标键盘事件  pyautogui

    def add_model_task(e):
        task_item_list.controls.append(task_item())
        page.update()

    def print_task_list(e):
        for e in list(map(lambda x:x.content.controls,list(filter(lambda x:x.data,task_item_list.controls)))):
            print(list(map(lambda x:x.value,e)))
    # click to change the task status
    def task_item_click(e):
        print("Item Clicked!!")
        handle_task_item_click(e.control)
        page.update()
    def handle_task_item_click(e:ft.Container):
        e.data=not e.data
        e.bgcolor=ft.Colors.GREEN_300 if e.data else ft.Colors.RED_300
    
    # mouse_task,mouse_name,position(int,int)
    def handle_mouse_task(task,name,position=None):
        match task:
            case config.MOUSE_TASK.moveTo.value:
                if position!=None:pyautogui.moveTo(position[0]*SC_WIDTH/int(camera_width.value),position[1]*SC_HEIGHT/int(camera_height.value))
            case config.MOUSE_TASK.mouse_up.value:
                pyautogui.mouseUp(button=name)
            case config.MOUSE_TASK.mouse_down.value:
                pyautogui.mouseDown(button=name)
            case config.MOUSE_TASK.click.value:
                pyautogui.click(button=name)

    # long press to delete the task
    def task_item_long_press(e):
        print("Item Long Press!!")
        task_item_list.controls.remove(e.control)
        page.update()

        """
        @return item=ft.Container
        @item attr:
            content.controls:
                [0].value=last_gesture_name
                [1].value=now_gesture_name
                [2].value=keypoint_id
                [3].value=mouse_task:
                    moveTo
                    mouse up
                    mouse down
                    click
                [4].value=mouse_name:
                    left
                    right
                    
                
            data=(bool)task_status{if detect this task}
        """
    def task_item():
        #[0]
        last_gesture_name=ft.DropdownM2(
            label="Last Gesture Name",
            value="all",
            options=list(map(lambda x:ft.dropdownm2.Option(x),list(i.value for i in config.GESTURE_NAME))),
            tooltip="Choose the gesture name",
        )
        #[1]
        now_gesture_name=ft.DropdownM2(
            label="Now Gesture Name",
            value="all",
            options=list(map(lambda x:ft.dropdownm2.Option(x),list(i.value for i in config.GESTURE_NAME))),
            tooltip="Choose the gesture name",
        )
        #[2]
        keypoint_id = ft.TextField(
            label="Keypoint ID",
            value=0,
        )
        #[3]
        mouse_task=ft.DropdownM2(
            label="Mouse Task",
            options=list(map(lambda x:ft.dropdownm2.Option(x),list(i.value for i in config.MOUSE_TASK)))
        )
        #[4]
        mouse_name=ft.DropdownM2(
            label="Mouse Name",
            options=list(map(lambda x:ft.dropdownm2.Option(x),list(i.value for i in config.MOUSE_NAME)))
        )

        item=ft.Container(
                content=ft.Column(
                    controls=[
                        last_gesture_name,
                        now_gesture_name,
                        keypoint_id,
                        mouse_task,
                        mouse_name
                    ]
                ),
                margin=10,
                padding=20,
                alignment=ft.alignment.center,
                bgcolor=ft.Colors.GREEN_300,
                width=100,
                border_radius=10,
                col={"sm":6,"md":4,"xl":2},
                on_click=task_item_click,
                on_long_press=task_item_long_press,
                data=True
            )
        return item

    task_item_list=ft.ResponsiveRow(controls=[])

    def change_pyautogui_PAUSE(e):
        pyautogui.PAUSE=float(e.control.value)
        print(float(e.control.value))

    model_task_panel=ft.ExpansionTile(
        title=ft.Row(
            controls=[
                ft.Text("Task"),
                ft.VerticalDivider(color=ft.Colors.WHITE),
                ft.FilledTonalButton(
                    text="Add Mouse Task",
                    icon=ft.Icons.ADD,
                    icon_color=ft.Colors.GREEN_300,
                    on_click=add_model_task,
                ),
                ft.TextButton(
                    text="Print Container",
                    on_click=print_task_list
                ),
                ft.TextField(
                    label="pyautogui_PAUSE",
                    value=0.1,
                    on_blur=change_pyautogui_PAUSE,
                    width=150
                )
            ]
        ),
        controls=[task_item_list]
    )
    
ft.app(target=main)