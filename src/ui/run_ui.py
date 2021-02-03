import os

import src.utils.converter as converter
import src.utils.general_utils as general_utils
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QMessageBox
from src.evaluators.coco_evaluator import get_coco_summary
from src.evaluators.pascal_voc_evaluator import (get_pascalvoc_metrics, plot_precision_recall_curve)
from src.ui.details import Details_Dialog
from src.ui.main_ui import Ui_Dialog as Main_UI
from src.ui.results import Results_Dialog
from src.utils.enumerators import BBFormat, BBType, CoordinatesType
import json


class Main_Dialog(QMainWindow, Main_UI):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.current_directory = os.path.dirname(os.path.realpath(__file__))
        # Define error msg dialog
        self.msgBox = QMessageBox()
        # Define details dialog
        self.dialog_statistics = Details_Dialog()
        # Define results dialog
        self.dialog_results = Results_Dialog()

        # Default values
        self.dir_annotations_gt = None
        self.dir_images_gt = None
        self.filepath_classes_gt = None
        self.dir_dets = None
        self.filepath_classes_det = None
        self.dir_save_results = None

    def closeEvent(self, event):
        conf = self.show_popup('Are you sure you want to close the program?',
                               'Closing',
                               buttons=QMessageBox.Yes | QMessageBox.No,
                               icon=QMessageBox.Question)
        if conf == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def show_popup(self,
                   message,
                   title,
                   buttons=QMessageBox.Ok | QMessageBox.Cancel,
                   icon=QMessageBox.Information):
        self.msgBox.setIcon(icon)
        self.msgBox.setText(message)
        self.msgBox.setWindowTitle(title)
        self.msgBox.setStandardButtons(buttons)
        return self.msgBox.exec()

    def load_annotations_gt(self):
        ret = []
        if self.rad_gt_format_coco_json.isChecked():
            ret = converter.coco2bb(self.dir_annotations_gt)
        elif self.rad_gt_format_cvat_xml.isChecked():
            ret = converter.cvat2bb(self.dir_annotations_gt)
        elif self.rad_gt_format_openimages_csv.isChecked():
            ret = converter.openimage2bb(self.dir_annotations_gt, self.dir_images_gt,
                                         BBType.GROUND_TRUTH)
        elif self.rad_gt_format_labelme_xml.isChecked():
            ret = converter.labelme2bb(self.dir_annotations_gt)
        elif self.rad_gt_format_pascalvoc_xml.isChecked():
            ret = converter.vocpascal2bb(self.dir_annotations_gt)
        elif self.rad_gt_format_imagenet_xml.isChecked():
            ret = converter.imagenet2bb(self.dir_annotations_gt)
        elif self.rad_gt_format_abs_values_text.isChecked():
            ret = converter.text2bb(self.dir_annotations_gt, bb_type=BBType.GROUND_TRUTH)
        elif self.rad_gt_format_yolo_text.isChecked():
            ret = converter.yolo2bb(self.dir_annotations_gt,
                                    self.dir_images_gt,
                                    self.filepath_classes_gt,
                                    bb_type=BBType.GROUND_TRUTH)
        # Make all types as GT
        [bb.set_bb_type(BBType.GROUND_TRUTH) for bb in ret]
        return ret

    def replace_id_with_classes(self, bounding_boxes, filepath_classes_det):
        classes = []
        f = open(self.filepath_classes_det, 'r')
        classes = [line.replace('\n', '') for line in f.readlines()]
        f.close()
        for bb in bounding_boxes:
            if not general_utils.is_str_int(bb.get_class_id()):
                print(
                    f'Warning: Class id represented in the {filepath_classes_det} is not a valid integer.'
                )
                return bounding_boxes
            class_id = int(bb.get_class_id())
            if class_id not in range(len(classes)):
                print(
                    f'Warning: Class id represented in the {filepath_classes_det} is not in the range of classes specified in the file {file_obj_names}.'
                )
                return bounding_boxes
            bb._class_id = classes[class_id]
        return bounding_boxes

    def load_annotations_det(self):
        ret = []
        # If relative format was required
        if self.rad_det_ci_format_text_xywh_rel.isChecked(
        ) or self.rad_det_cn_format_text_xywh_rel.isChecked():
            # Verify if directory with images was provided
            if self.dir_images_gt is None or not os.path.isdir(self.dir_images_gt):
                self.show_popup(
                    f'For the selected annotation type, it is necessary to inform a directory with the dataset images.\nDirectory is empty or does not have valid images.',
                    'Invalid image directory',
                    buttons=QMessageBox.Ok,
                    icon=QMessageBox.Information)
                return ret, False
        if self.rad_det_format_coco_json.isChecked():
            ret = converter.coco2bb(self.dir_dets, bb_type=BBType.DETECTED)
        elif self.rad_det_ci_format_text_xywh_rel.isChecked(
        ) or self.rad_det_cn_format_text_xywh_rel.isChecked():
            ret = converter.text2bb(self.dir_dets,
                                    bb_type=BBType.DETECTED,
                                    bb_format=BBFormat.XYWH,
                                    type_coordinates=CoordinatesType.RELATIVE,
                                    img_dir=self.dir_images_gt)
        elif self.rad_det_ci_format_text_xyx2y2_abs.isChecked(
        ) or self.rad_det_cn_format_text_xyx2y2_abs.isChecked():
            ret = converter.text2bb(self.dir_dets,
                                    bb_type=BBType.DETECTED,
                                    bb_format=BBFormat.XYX2Y2,
                                    type_coordinates=CoordinatesType.ABSOLUTE,
                                    img_dir=self.dir_images_gt)
        elif self.rad_det_ci_format_text_xywh_abs.isChecked(
        ) or self.rad_det_cn_format_text_xywh_abs.isChecked():
            ret = converter.text2bb(self.dir_dets,
                                    bb_type=BBType.DETECTED,
                                    bb_format=BBFormat.XYWH,
                                    type_coordinates=CoordinatesType.ABSOLUTE,
                                    img_dir=self.dir_images_gt)

        # if its format is in a format that requires class_id, replace the class_id by the class name
        if self.rad_det_ci_format_text_xywh_rel.isChecked(
        ) or self.rad_det_ci_format_text_xyx2y2_abs.isChecked(
        ) or self.rad_det_ci_format_text_xywh_abs.isChecked():
            if self.filepath_classes_det is None or os.path.isfile(
                    self.filepath_classes_det) is False or len(
                        general_utils.get_files_dir(
                            self.dir_images_gt,
                            extensions=['jpg', 'jpge', 'png', 'bmp', 'tiff', 'tif'])) == 0:
                self.show_popup(
                    f'For the selected annotation type, it is necessary to inform a directory with the dataset images.\nDirectory is empty or does not have valid images.',
                    'Invalid image directory',
                    buttons=QMessageBox.Ok,
                    icon=QMessageBox.Information)
                return ret, False
            ret = self.replace_id_with_classes(ret, self.filepath_classes_det)
        if len(ret) == 0:
            self.show_popup(
                f'No files was found in the selected directory for the selected annotation format.\nDirectory is empty or does not have valid annotation files.',
                'Invalid directory',
                buttons=QMessageBox.Ok,
                icon=QMessageBox.Information)
            return ret, False
        return ret, True

    def btn_gt_statistics_clicked(self):
        # If yolo format is selected, file with classes must be informed
        if self.rad_gt_format_yolo_text.isChecked():
            if self.filepath_classes_gt is None or os.path.isfile(
                    self.filepath_classes_gt) is False:
                self.show_popup(
                    'For the selected groundtruth format, a valid file with classes must be informed.',
                    'Invalid file',
                    buttons=QMessageBox.Ok,
                    icon=QMessageBox.Information)
                return

        gt_annotations = self.load_annotations_gt()
        if gt_annotations is None or len(gt_annotations) == 0:
            self.show_popup(
                'Directory with ground-truth annotations was not specified or do not contain annotations in the chosen format.',
                'Annotations not found',
                buttons=QMessageBox.Ok,
                icon=QMessageBox.Information)
            return
        if self.dir_images_gt is None:
            self.show_popup(
                'Directory with ground-truth images was not specified or do not contain images.',
                'Images not found',
                buttons=QMessageBox.Ok,
                icon=QMessageBox.Information)
            return
        # Open statistics dialot on the gt annotations
        self.dialog_statistics.show_dialog(BBType.GROUND_TRUTH, gt_annotations, None,
                                           self.dir_images_gt)

    def btn_gt_dir_clicked(self):
        if self.txb_gt_dir.text() == '':
            txt = self.current_directory
        else:
            txt = self.txb_gt_dir.text()
        directory = QFileDialog.getExistingDirectory(
            self, 'Choose directory with ground truth annotations', txt)
        if directory == '':
            return
        if os.path.isdir(directory):
            self.txb_gt_dir.setText(directory)
            self.dir_annotations_gt = directory
        else:
            self.dir_annotations_gt = None

    def btn_gt_classes_clicked(self):
        filepath = QFileDialog.getOpenFileName(self, 'Choose a file with a list of classes',
                                               self.current_directory,
                                               "Image files (*.txt *.names)")
        filepath = filepath[0]
        if os.path.isfile(filepath):
            self.txb_classes_gt.setText(filepath)
            self.filepath_classes_gt = filepath
        else:
            self.filepath_classes_gt = None

    def btn_gt_images_dir_clicked(self):
        if self.txb_gt_images_dir.text() == '':
            txt = self.current_directory
        else:
            txt = self.txb_gt_images_dir.text()
        directory = QFileDialog.getExistingDirectory(self,
                                                     'Choose directory with ground truth images',
                                                     txt)
        if directory != '':
            self.txb_gt_images_dir.setText(directory)
            self.dir_images_gt = directory

    def btn_det_classes_clicked(self):
        filepath = QFileDialog.getOpenFileName(self, 'Choose a file with a list of classes',
                                               self.current_directory,
                                               "Image files (*.txt *.names)")
        filepath = filepath[0]
        if os.path.isfile(filepath):
            self.txb_classes_det.setText(filepath)
            self.filepath_classes_det = filepath
        else:
            self.filepath_classes_det = None

    def btn_det_dir_clicked(self):
        if self.txb_det_dir.text() == '':
            txt = self.current_directory
        else:
            txt = self.txb_det_dir.text()
        directory = QFileDialog.getExistingDirectory(self, 'Choose directory with detections', txt)
        if directory == '':
            return
        if os.path.isdir(directory):
            self.txb_det_dir.setText(directory)
            self.dir_dets = directory
        else:
            self.dir_dets = None

    def btn_statistics_det_clicked(self):
        det_annotations, passed = self.load_annotations_det()
        if passed is False:
            return
        gt_annotations = self.load_annotations_gt()
        if self.dir_images_gt is None or os.path.isdir(self.dir_images_gt) is False:
            self.show_popup(
                'Directory with ground-truth images was not specified or do not contain images.',
                'Images not found',
                buttons=QMessageBox.Ok,
                icon=QMessageBox.Information)
            return
        # Open statistics dialog on the detections
        self.dialog_statistics.show_dialog(BBType.DETECTED, gt_annotations, det_annotations,
                                           self.dir_images_gt)

    def btn_output_dir_clicked(self):
        if self.txb_output_dir.text() == '':
            txt = self.current_directory
        else:
            txt = self.txb_output_dir.text()
        directory = QFileDialog.getExistingDirectory(self, 'Choose directory to save the results',
                                                     txt)
        if os.path.isdir(directory):
            self.txb_output_dir.setText(directory)
            self.dir_save_results = directory
        else:
            self.dir_save_results = None

    def btn_run_clicked(self):
        if self.dir_save_results is None or os.path.isdir(self.dir_save_results) is False:
            self.show_popup('Output directory to save results was not specified or does not exist.',
                            'Invalid output directory',
                            buttons=QMessageBox.Ok,
                            icon=QMessageBox.Information)
            return
        # Get detections
        det_annotations, passed = self.load_annotations_det()
        if passed is False:
            return
        # Verify if there are detections
        if det_annotations is None or len(det_annotations) == 0:
            self.show_popup(
                'No detection of the selected type was found in the folder.\nCheck if the selected type corresponds to the files in the folder and try again.',
                'Invalid detections',
                buttons=QMessageBox.Ok,
                icon=QMessageBox.Information)
            return

        gt_annotations = self.load_annotations_gt()
        if gt_annotations is None or len(gt_annotations) == 0:
            self.show_popup(
                'No bounding box of the selected type was found in the folder.\nCheck if the selected type corresponds to the files in the folder and try again.',
                'Invalid groundtruths',
                buttons=QMessageBox.Ok,
                icon=QMessageBox.Information)
            return

        coco_res = {}
        pascal_res = {}
        # If any coco metric is required
        if self.chb_metric_AP_coco.isChecked() or self.chb_metric_AP50_coco.isChecked(
        ) or self.chb_metric_AP75_coco.isChecked() or self.chb_metric_APsmall_coco.isChecked(
        ) or self.chb_metric_APmedium_coco.isChecked() or self.chb_metric_APlarge_coco.isChecked(
        ) or self.chb_metric_AR_max1.isChecked() or self.chb_metric_AR_max10.isChecked(
        ) or self.chb_metric_AR_max100.isChecked() or self.chb_metric_AR_small.isChecked(
        ) or self.chb_metric_AR_medium.isChecked() or self.chb_metric_AR_large.isChecked():
            coco_res = get_coco_summary(gt_annotations, det_annotations)
            # Remove not checked metrics
            if not self.chb_metric_AP_coco.isChecked():
                del coco_res['AP']
            if not self.chb_metric_AP50_coco.isChecked():
                del coco_res['AP50']
            if not self.chb_metric_AP75_coco.isChecked():
                del coco_res['AP75']
            if not self.chb_metric_APsmall_coco.isChecked():
                del coco_res['APsmall']
            if not self.chb_metric_APmedium_coco.isChecked():
                del coco_res['APmedium']
            if not self.chb_metric_APlarge_coco.isChecked():
                del coco_res['APlarge']
            if not self.chb_metric_AR_max1.isChecked():
                del coco_res['AR1']
            if not self.chb_metric_AR_max10.isChecked():
                del coco_res['AR10']
            if not self.chb_metric_AR_max100.isChecked():
                del coco_res['AR100']
            if not self.chb_metric_AR_small.isChecked():
                del coco_res['ARsmall']
            if not self.chb_metric_AR_medium.isChecked():
                del coco_res['ARmedium']
            if not self.chb_metric_AR_large.isChecked():
                del coco_res['ARlarge']
        # If any pascal metric is required
        if self.chb_metric_AP_pascal.isChecked() or self.chb_metric_mAP_pascal.isChecked():
            iou_threshold = self.dsb_IOU_pascal.value()
            pascal_res = get_pascalvoc_metrics(gt_annotations,
                                               det_annotations,
                                               iou_threshold=iou_threshold,
                                               generate_table=True)
            if not self.chb_metric_AP_pascal.isChecked():
                del pascal_res['per_class']
            if not self.chb_metric_AR_large.isChecked():
                del pascal_res['mAP']

            if 'per_class' in pascal_res:
                # Save plots
                plot_precision_recall_curve(pascal_res['per_class'],
                                            showAP=True,
                                            savePath=self.dir_save_results,
                                            showGraphic=False)

        if len(coco_res) + len(pascal_res) == 0:
            self.show_popup('No results to show',
                            'No results',
                            buttons=QMessageBox.Ok,
                            icon=QMessageBox.Information)
        else:
            with open(self.dir_save_results + '/metrics.json', 'w') as metric_file:
                data = {}
                data['pascal-voc'] = []
                data['coco'] = []
                data['coco'].append({
                    'AP50': str(coco_res['AP50']),
                    'AP75': str(coco_res['AP75'])
                })
                data['pascal-voc'].append({
                    'IOU': str(iou_threshold)
                })
                for class_name in pascal_res['per_class']:
                    key_name = class_name + '_AP'
                    data['pascal-voc'].append({
                        key_name: str(pascal_res['per_class'][class_name]['AP'])
                    })
                data['pascal-voc'].append({
                    'mAP': str(pascal_res['mAP'])
                })
                json.dump(data, metric_file)

            self.dialog_results.show_dialog(coco_res, pascal_res, self.dir_save_results)
